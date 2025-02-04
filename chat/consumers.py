import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import AnonymousUser
from .models import ChatRoom, Message
from users.models import User
from django.utils import timezone
from django.db.models import Q
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        웹소켓 연결을 처리하는 메서드
        1. 클라이언트가 채팅방에 접속하면 실행됨.
        2. JWT 토큰을 검증하여 사용자를 인증함.
        3. 사용자가 채팅방에 참여할 수 있는지 확인.
        4. 채팅방에 그룹 추가 후 연결을 수락.
        5. 기존 채팅 메시지를 전송.
        """
        self.room_id = self.scope['url_route']['kwargs']['room_id'] # URL에서 채팅방 ID 가져오기
        self.room_group_name = f'chat_{self.room_id}'  # 채팅방 그룹 이름 지정
        
        # JWT 토큰 기반 사용자 인증
        try:
            query_string = self.scope['query_string'].decode()
            token = query_string.split('=')[1] if '=' in query_string else ''
            print(f"Received token: {token}")
            self.user = await self.get_user_from_token(token) # 토큰을 기반으로 사용자 가져오기
        except Exception as e:
            print(f"Error during token extraction: {e}")
            await self.close()  # 인증 실패 시 연결 종료
            return

        # 채팅방 참여 여부 확인
        if await self.validate_participation():
            # 채팅방 그룹에 현재 웹소켓 채널 추가
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()  # 웹소켓 연결 수락
            await self.send_existing_messages() # 기존 메시지 전송
        else:
            await self.close()
    
    # 참여 여부 확인 메서드
    @database_sync_to_async
    def validate_participation(self):
        """현재 사용자가 해당 채팅방에 참여 중인지 확인"""
        return ChatRoom.objects.filter(
            Q(user1=self.user) | Q(user2=self.user),  # user1 또는 user2가 현재 사용자와 일치하는지 확인
            id=self.room_id
        ).exists()

    @database_sync_to_async
    def get_room(self):
        """채팅방 가져오기"""
        return ChatRoom.objects.get(id=self.room_id)

    async def send_existing_messages(self):
            # 기존 메시지 불러오기
        room = await self.get_room()
        messages = await database_sync_to_async(
            lambda: list(room.messages.order_by('timestamp').select_related('sender'))
        )()

        for message in messages:
            await self.send(text_data=json.dumps({
                'message_id': message.id,
                'content': message.content,
                'sender_id': message.sender.id,
                'sender_nickname': message.sender.nickname,
                'profile_image': message.sender.profile_image.url if message.sender.profile_image else None,
                'timestamp': message.timestamp.isoformat(),
                'is_read': await database_sync_to_async(lambda: self.user in message.read_by.all())()  # 현재 사용자가 읽었는지 여부
            }))

    # 메시지 수신
    async def receive(self, text_data):
        data = json.loads(text_data)  # JSON 데이터 파싱
        message_content = data['content']  # 메시지 내용 추출
        
        msg = await self.save_message(message_content)  # 메시지를 db에 저장
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',  # chat_message 이벤트 핸들러 호출
                'message_id': msg.id,
                'content': msg.content,
                'sender_id': self.user.id,
                'sender_nickname': self.user.nickname,
                'profile_image': self.user.profile_image.url if self.user.profile_image else None,
                'timestamp': msg.timestamp.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))  # 클라이언트에게 메시지 전송
        if event['sender_id'] != self.user.id:  # 본인이 보낸 메시지가 아닐 경우 => 메시지 읽음 처리
            await self.mark_as_read(event['message_id'])

    @database_sync_to_async
    def save_message(self, content):
        """메시지를 데이터베이스에 저장하고 반환"""
        room = ChatRoom.objects.get(id=self.room_id)  # 채팅방 가져오기
        message = Message.objects.create(
            room=room,
            sender=self.user,
            content=content
        )
        message.read_by.add(self.user)  # 보낸 사람은 자동으로 읽음 처리
        room.update_last_message_time()  # 채팅방의 마지막 메시지 시간 업데이트
        return message

    @database_sync_to_async
    def mark_as_read(self, message_id):
        """메시지를 읽음 처리"""
        message = Message.objects.get(id=message_id)
        message.read_by.add(self.user)

    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        JWT 토큰을 검증하고 사용자 객체를 반환.
        1. 토큰을 사용하여 사용자 ID를 가져옴.
        2. ID를 기반으로 사용자 객체를 조회.
        3. 유효하지 않은 토큰이면 AnonymousUser 반환.
        """
        if not token:
            return self.scope.get("user", AnonymousUser())
    
        try:
            UntypedToken(token)
            user = User.objects.get(id=UntypedToken(token).payload['user_id'])  # 토큰에서 사용자 ID 추출 후 조회
            return user
        except (InvalidToken, TokenError, User.DoesNotExist):
            return AnonymousUser()  # 인증 실패 시 익명 사용자 반환

