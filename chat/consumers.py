import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import AnonymousUser
from .models import ChatRoom, Message
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()

# 로거 생성 (DEBUG 레벨)
logger = logging.getLogger("chat.consumer")
logger.setLevel(logging.DEBUG)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.debug("CONNECT 시도")
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"chat_{self.room_id}"
        logger.debug(f"Room ID: {self.room_id}, Group: {self.room_group_name}")

        # 쿼리스트링에서 토큰 추출
        query_string = self.scope['query_string'].decode()
        token = ""
        if query_string:
            parts = query_string.split('=')
            if len(parts) > 1:
                token = parts[1]
        logger.debug(f"추출된 토큰: {token}")

        self.user = await self.get_user_from_token(token)
        logger.debug(f"사용자: {self.user}")

        if not await self.validate_participation():
            logger.error("참여 권한 없음 - 연결 종료")
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.debug("WebSocket 연결 수락됨 및 그룹 가입 완료")

        messages = await self.get_existing_messages()
        logger.debug(f"기존 메시지 {len(messages)}개 전송")
        await self.send(text_data=json.dumps({
            "type": "chat.history",
            "messages": messages,
        }))

    async def disconnect(self, close_code):
        logger.debug(f"DISCONNECT: {close_code}")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        logger.debug(f"RECEIVE: {text_data}")
        data = json.loads(text_data)
        if data.get("command") == "fetch_messages":
            messages = await self.get_existing_messages()
            await self.send(text_data=json.dumps({
                "type": "chat.history",
                "messages": messages,
            }))
        elif data.get("content"):
            message_content = data["content"]
            logger.debug(f"받은 메시지 내용: {message_content}")
            msg = await self.save_message(message_content)
            event = {
                "type": "chat.message",
                "message_id": msg.id,
                "content": msg.content,
                "sender_id": self.user.id,
                "sender_nickname": self.user.username,
                "timestamp": msg.timestamp.isoformat(),
            }
            logger.debug(f"Broadcast event: {event}")
            logger.debug(f"Adding client to group: {self.room_group_name}")
            await self.channel_layer.group_send(self.room_group_name, event)

    async def chat_message(self, event):
        logger.debug(f"chat_message 호출됨, event: {event}")
        await self.send(text_data=json.dumps(event))
        if event["sender_id"] != self.user.id:
            await self.mark_as_read(event["message_id"])

    @database_sync_to_async
    def get_existing_messages(self):
        room = ChatRoom.objects.get(id=self.room_id)
        messages = list(room.messages.order_by("timestamp").select_related("sender"))
        msg_list = []
        for message in messages:
            is_read = message.read_by.filter(id=self.user.id).exists()
            msg_list.append({
                "message_id": message.id,
                "content": message.content,
                "sender_id": message.sender.id,
                "sender_nickname": message.sender.username,
                "timestamp": message.timestamp.isoformat(),
                "is_read": is_read,
            })
        return msg_list

    @database_sync_to_async
    def validate_participation(self):
        return ChatRoom.objects.filter(Q(user1=self.user) | Q(user2=self.user), id=self.room_id).exists()

    @database_sync_to_async
    def save_message(self, content):
        logger.debug(f"save_message 호출됨: {content}")
        room = ChatRoom.objects.get(id=self.room_id)
        message = Message.objects.create(room=room, sender=self.user, content=content)
        message.read_by.add(self.user)
        room.update_last_message_time()

        # 메시지 전송을 위한 로그 추가
        logger.debug(f"메시지 저장 완료: {message.id}, {message.content}")

        # 중복된 메시지 전송 제거
        self.send_message_to_clients(message)  # 메시지 전송
        return message

    
    def send_message_to_clients(self, message):
        logger.debug(f"센드메시지투클라이언트호출")
    # event 객체 생성
        event = {
            "type": "chat.message",  # 이벤트 타입
            "message_id": message.id,  # 메시지 ID
            "content": message.content,  # 메시지 내용
            "sender_id": message.sender.id,  # 보낸 사람의 ID
            "sender_nickname": message.sender.username,  # 보낸 사람의 닉네임
            "timestamp": message.timestamp.isoformat(),  # 메시지 전송 시간
        }
        
        # 로그 추가: event가 제대로 생성되는지 확인
        logger.debug(f"Sending message to clients: {event}")
        
        # 그룹에 메시지 전송
        self.channel_layer.group_send(self.room_group_name, event)


    @database_sync_to_async
    def mark_as_read(self, message_id):
        message = Message.objects.get(id=message_id)
        message.read_by.add(self.user)

    @database_sync_to_async
    def get_user_from_token(self, token):
        if not token:
            return self.scope.get("user", AnonymousUser())
        try:
            validated_token = UntypedToken(token)
            user_id = validated_token.payload.get("user_id")
            user = User.objects.get(id=user_id)
            return user
        except (InvalidToken, TokenError, User.DoesNotExist):
            return AnonymousUser()
