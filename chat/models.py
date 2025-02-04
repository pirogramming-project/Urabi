from django.db import models
from users.models import User
from accompany.models import TravelGroup
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.core.cache import cache

class ChatRoom(models.Model):
    """
    채팅방을 나타내는 모델
    - 특정 여행 그룹(TravelGroup) 내에서 두 명의 사용자가 채팅을 할 수 있음.
    - user1, user2 필드를 통해 참가자 2명을 저장.
    - last_message_time을 사용하여 마지막 메시지 시간을 저장.
    """
    
    travel = models.ForeignKey(TravelGroup, on_delete=models.CASCADE, related_name='chat_rooms') # 특정 여행 그룹(TravelGroup)에 속한 채팅방
    user1 = models.ForeignKey(User, related_name='user1_chatrooms', on_delete=models.CASCADE) # 참가자 1
    user2 = models.ForeignKey(User, related_name='user2_chatrooms', on_delete=models.CASCADE) # 참가자 2
    created_at = models.DateTimeField(auto_now_add=True)  # 채팅방 생성 시간
    last_message_time = models.DateTimeField(null=True, blank=True) # 마지막 메시지 전송 시간 

    class Meta:
        unique_together = ('user1', 'user2', 'travel')  # 같은 여행 그룹에서 같은 두 사용자가 중복된 채팅방을 만들지 않도록 제한

    def __str__(self):
        """채팅방을 문자열로 표현할 때 user1 - user2 (여행 제목) 형식으로 출력"""
        return f"{self.user1.nickname} - {self.user2.nickname} ({self.travel.title})"

    def update_last_message_time(self):
        """
        채팅방의 마지막 메시지 시간을 현재 시간으로 업데이트하고 저장
        새로운 메시지가 생성될 때 호출
        """
        self.last_message_time = timezone.now()
        self.save()
    
    @property
    @cache_page(60*500)
    def get_last_message(self):
        """
        채팅방의 마지막 메시지를 반환하며, 5분 동안 캐싱함.
        """
        cache_key = f'chatroom_{self.id}_last_message'  # 캐시 키 생성
        last_msg = cache.get(cache_key)  # 캐시에서 가져오기

        if last_msg is None:
            last_msg = self.messages.order_by('-timestamp').first()  # 마지막 메시지 가져오기
            cache.set(cache_key, last_msg, timeout=60 * 5)  # 5분 동안 캐싱

        return last_msg

class Message(models.Model):
    """
    채팅 메시지를 저장하는 모델
    - 특정 채팅방(ChatRoom)에 속한 메시지
    - 메시지를 보낸 사용자(sender)
    - 메시지 내용(content)
    - 메시지가 전송된 시간(timestamp)
    - 읽은 사용자 목록(read_by)
    """
    room = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)

    def __str__(self):
        """메시지를 문자열로 표현할 때 '보낸 사람: 메시지 내용' 형식으로 출력"""
        return f"{self.sender.nickname}: {self.content[:20]}"

    def save(self, *args, **kwargs):
        """
        메시지를 저장할 때 실행되는 메서드
        - 메시지가 새로 생성될 경우(last_message_time을 업데이트)
        """
        is_new = self.pk is None
        super().save(*args, **kwargs) # 부모 클래스의 save() 실행
        if is_new:
            self.room.update_last_message_time() # 채팅방의 마지막 메시지 시간 업데이트