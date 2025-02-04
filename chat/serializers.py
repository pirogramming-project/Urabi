from rest_framework import serializers
from .models import ChatRoom, Message
from users.models import User

class UserSerializer(serializers.ModelSerializer):
    """
    사용자 정보 직렬화 클래스
    - 목적: 사용자 모델의 특정 필드를 API 응답에 포함시키기 위해 사용
    - 포함 필드:
      - id: 사용자 고유 식별자
      - nickname: 사용자 닉네임
      - profile_image: 프로필 이미지 URL
    """
    class Meta:
        model = User
        fields = ['id', 'nickname', 'profile_image']

class MessageSerializer(serializers.ModelSerializer):
    """
    채팅 메시지 직렬화 클래스
    - 메시지 모델의 데이터를 JSON 형식으로 변환
      - sender 필드는 UserSerializer를 사용해 중첩 직렬화
      - read_by: 메시지를 읽은 사용자 목록
    """
    
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'content', 'timestamp', 'read_by']

class ChatRoomSerializer(serializers.ModelSerializer):
    """
    채팅방 상세 정보 직렬화 클래스
    - 채팅방의 모든 세부 정보 표현
      - user1/user2: 중첩된 사용자 정보 표현
      - travel: 연결된 여행 그룹 ID 자동 포함
    """
    user1 = UserSerializer(read_only=True)  # 사용자1 상세 정보
    user2 = UserSerializer(read_only=True)  # 사용자2 상세 정보
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'user1', 'user2', 'travel', 'created_at']
    
    def create(self, validated_data):
        # request를 context에서 가져옴 (view에서 serializer를 생성할 때 context={'request': request} 전달되어야 함)
        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context is required.")
        
        # 자동으로 user1은 요청한 사용자로 설정
        validated_data['user1'] = request.user

        # read_only 필드이므로, 입력 데이터는 self.initial_data 에 
        # (모델에서 외래키 필드 이름이 user2, travel이라면 그대로 사용)
        if 'user2' in self.initial_data:
            validated_data['user2_id'] = self.initial_data['user2']
        if 'travel' in self.initial_data:
            validated_data['travel_id'] = self.initial_data['travel']

        return super().create(validated_data)

class ChatRoomInfoSerializer(serializers.Serializer):
    """
    채팅방 목록 표시용 최적화 직렬화 클래스
    - 채팅방 목록에서 필요한 정보만 전달
    - 데이터:
      - id: 채팅방 ID
      - other_user_*: 상대방 사용자 정보
      - last_message_*: 최근 메시지 정보
      - unread_count: 안 읽은 메시지 수
      - travel_title: 연결된 여행 제목
    """
    id = serializers.IntegerField()
    other_user_id = serializers.IntegerField()
    other_user_nickname = serializers.CharField()
    other_user_profile_image = serializers.URLField(allow_null=True) # 이미지 없을 경우 null
    last_message_content = serializers.CharField(allow_null=True)    # 메시지 없을 경우 null
    last_message_timestamp = serializers.DateTimeField(allow_null=True)
    unread_count = serializers.IntegerField()
    travel_title = serializers.CharField()   # TravelGroup의 title 필드 매핑

class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """
    [NEW] 채팅방 상세 정보를 표시하기 위한 직렬화 클래스
    - 필요에 따라 user1, user2, 메시지 목록 등 세부 정보를 포함할 수 있음.
    """
    user1 = UserSerializer(read_only=True)
    user2 = UserSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatRoom
        fields = [
            'id',
            'user1',
            'user2',
            'travel',
            'created_at',
            'last_message_time',  
            'messages',
        ]