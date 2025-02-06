from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.conf import settings
from .models import User
import requests
from django.core.files.storage import FileSystemStorage
import json
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import render, get_object_or_404
from .models import User, TravelPlan
from accompany.models import Accompany_Zzim, TravelParticipants, TravelGroup
from .serializers import SignupSerializer, UserSerializer, LoginSerializer
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, TravelPlanForm
from django.core.files.base import ContentFile
from accommodation.models import AccommodationReview


def social_login(request):
    return render(request, 'users/social_login.html')

def kakao_login(request):
    client_id = settings.KAKAO_API_KEY
    redirect_uri = "http://127.0.0.1:8000/users/login/kakao/callback/"
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
    )

def kakao_login_callback(request):
    code = request.GET.get("code")
    client_id = settings.KAKAO_API_KEY
    redirect_uri = "http://127.0.0.1:8000/users/login/kakao/callback/"  

    token_request = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code": code,
        },
    )
    token_json = token_request.json()
    
    if "error" in token_json:
        return redirect('users:login')

    access_token = token_json.get("access_token")
    
    profile_request = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile_json = profile_request.json()
    
    kakao_account = profile_json.get("kakao_account", {})
    email = kakao_account.get("email")
    properties = profile_json.get("properties", {})

    kakao_id = profile_json.get("id")
    username = kakao_account.get("profile", {}).get("nickname", f"kakao_{kakao_id}")
    profile_image = properties.get("profile_image")
    birth = kakao_account.get("birthday")
    birth_year = kakao_account.get("birthyear")

    gender = kakao_account.get("gender")
    gender_map = {"male": "M", "female": "F"}
    user_gender = gender_map.get(gender, "U")
    phone_number = kakao_account.get("phone_number")


    full_birth = None

    if birth and birth_year:
        full_birth = f"{birth_year}-{birth[:2]}-{birth[2:]}"

    if not email:
        email = f"kakao_{kakao_id}@example.com"  # 카카오 ID를 활용한 임시 이메일 생성
        properties = profile_json.get("properties", {})
        nickname = properties.get("nickname")
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        user = User.objects.create_user(
            email=email,
            social_id=f"kakao_{profile_json.get('id')}",
            username=username,
            nickname=username,
            birth=full_birth,
            user_gender=user_gender,
            user_phone=phone_number
        )
        if profile_image:
            response = requests.get(profile_image)
            if response.status_code == 200:
                image_name = f"profile_images/{user.email.replace('@', '_')}.jpg"
                user.profile_image.save(image_name, ContentFile(response.content))
        user.save()
    login(request, user)
    return redirect('main:home')  

def naver_login(request):
    client_id = settings.NAVER_CLIENT_ID
    redirect_uri = "http://127.0.0.1:8000/users/login/naver/callback/"
    state = "RANDOM_STATE"
    
    return redirect(
        f"https://nid.naver.com/oauth2.0/authorize?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )

def naver_login_callback(request):
    client_id = settings.NAVER_CLIENT_ID
    client_secret = settings.NAVER_CLIENT_SECRET
    redirect_uri = "http://127.0.0.1:8000/users/login/naver/callback/"  
    code = request.GET.get("code")
    state = request.GET.get("state")
    
    token_request = requests.post(
        "https://nid.naver.com/oauth2.0/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "state": state,
        },
    )
    token_json = token_request.json()
    
    if "error" in token_json:
        return redirect("/")
        
    access_token = token_json.get("access_token")
    profile_request = requests.get(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile_json = profile_request.json()
    
    if profile_json.get("resultcode") != "00":
        return redirect("/")
        
    response = profile_json.get("response")
    email = response.get("email")
    name = response.get("name")
    profile_image_url = response.get("profile_image")
    birth = response.get("birthday")
    birth_year = response.get("birthyear")
    phone_number = response.get("mobile")
    gender_map = {"M": "M", "F": "F"}
    user_gender = gender_map.get(response.get("gender"), "U")

    full_birth = None
    if birth and birth_year:
        full_birth = f"{birth_year}-{birth[:2]}-{birth[3:]}"
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        user = User.objects.create_user(
            email=email,
            social_id=f"naver_{response.get('id')}",
            username=name,
            nickname=name,
             birth=full_birth,
            user_gender=user_gender,
            user_phone=phone_number
        )
        if profile_image_url:
            response = requests.get(profile_image_url)  # 이미지 다운로드
            if response.status_code == 200:
                image_name = f"profile_images/{user.email.replace('@', '_')}.jpg"
                user.profile_image.save(image_name, ContentFile(response.content))
        
        user.save()
    
    login(request, user)
    return redirect('main:home')

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        if request.content_type == 'application/json':
            email = request.data.get('email')
            password = request.data.get('password')
            user = authenticate(email=email, password=password)

            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "token": str(refresh.access_token),
                    "user": {
                        "user_id": user.id,
                        "nickname": user.nickname,
                        "profile_image": user.profile_image.url if user.profile_image else None,
                    }
                }, status=status.HTTP_200_OK)
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            email = request.POST.get('email')
            password = request.POST.get('password')
            user = authenticate(email=email, password=password)
            
            if user:
                login(request, user)
                return redirect('main:home')
            return render(request, 'login/login.html', {'error': '로그인 실패'})

    def get(self, request):
        return render(request, 'login/login.html')

def signup_view(request):
    if request.method == 'POST':
        try:
            email = request.POST.get('email', "").strip()
            password = request.POST.get('password', "").strip()
            name = request.POST.get('name', "").strip()
            nickname = request.POST.get('nickname', "").strip()
            birth_year = request.POST.get('birth-year', "").strip()
            birth_month = request.POST.get('birth-month', "").strip()
            birth_day = request.POST.get('birth-day', "").strip()
            phone = request.POST.get('phone', "").strip()
            gender = request.POST.get('gender', "").strip()
            profile_image = request.FILES.get('profile-picture')

            print(f"📢 회원가입 요청: email={email}, name={name}, nickname={nickname}")

            # 🔹 이메일 중복 체크
            if User.objects.filter(email=email).exists():
                return render(request, 'register/register.html', {'error': '이미 존재하는 이메일입니다.'})

            # 🔹 성별 값 변환 (default: 'U' Unknown)
            gender_map = {"male": "M", "female": "F"}
            user_gender = gender_map.get(gender, "U")

            # 🔹 닉네임 기본값 설정
            if not nickname:
                nickname = name or "사용자"

            # 🔹 생년월일 설정
            if birth_year and birth_month and birth_day:
                birth = f"{birth_year}-{birth_month}-{birth_day}"
            else:
                birth = None  # 기본값 설정 가능

            # 🔹 나이 계산 (예외 방지)
            try:
                from datetime import datetime
                current_year = datetime.now().year
                user_age = current_year - int(birth_year) if birth_year.isdigit() else None
            except Exception as e:
                print(f"⚠️ 나이 계산 오류: {e}")
                user_age = None

            # 🔹 사용자 생성
            user = User.objects.create_user(
                email=email,
                password=password,
                username=name or nickname,
                nickname=nickname,
                birth=birth,
                user_age=user_age,
                user_gender=user_gender,
                user_phone=phone
            )

            # 🔹 프로필 이미지 저장
            if profile_image:
                user.profile_image = profile_image
            else:
                user.profile_image = 'profile_images/default-profile.png'  # 기본 프로필 지정

            user.save()
            print(f"✅ 회원가입 성공: {user.email}")

            # 🔹 회원가입 후 자동 로그인
            login(request, user)
            return redirect('main:home')

        except Exception as e:
            print(f"❌ 회원가입 중 오류 발생: {e}") 
            return render(request, 'register/register.html', {'error': str(e)})

    return render(request, 'register/register.html')


def user_logout(request):
    logout(request)
    return redirect('main:home')

def login_view(request):
    return render(request, 'main/main.html', {'user': request.user})



# 마이페이지 설정
@login_required
def my_page(request):
    return render(request, 'mypage/myPage.html', {'user':request.user})

# 정보 수정
@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)

        birth_year = request.POST.get("birth_year")
        birth_month = request.POST.get("birth_month")
        birth_day = request.POST.get("birth_day")

        if 'profile_image' in request.FILES:
            print("✅ 파일 업로드 감지됨!")
        else:
            print("⚠️ 파일 업로드가 안 됨")


        if birth_year and birth_month and birth_day:
            request.user.birth = f"{birth_year}-{birth_month}-{birth_day}"  # YYYY-MM-DD 형식으로 변환하여 저장

        if form.is_valid():
            form.save()
            request.user.save() 
            return redirect('users:my_page')
        else:
            print(form.errors)  # 디버깅용 출력

    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'mypage/editProfile.html', {'form': form, 'user': request.user})

@login_required
def my_trip(request):
    if request.method == 'POST':
        form = TravelPlanForm(request.POST)

        if form.is_valid():
            travel_plan = form.save(commit=False)
            travel_plan.created_by = request.user

            travel_plan.markers = request.POST.get('markers', '')  # 기본값 ''
            travel_plan.polyline = request.POST.get('polyline', '')

            travel_plan.save()  

            return render(request, 'mypage/plan_detail.html', {
                'travel_plan': travel_plan,
            })
    else:
        form = TravelPlanForm()

    return render(request, 'mypage/myTrip.html', {
        'form': form,
    })

@login_required
def user_detail(request, pk):
    user = get_object_or_404(User, id=pk)
    current_user = request.user  # 현재 로그인한 사용자
    
    # 여행 계획 및 동행 관련 쿼리 작성 
    user_plans = TravelPlan.objects.filter(created_by=user)
    user_accompany = TravelGroup.objects.filter(created_by=user)
    accompany_count = user_accompany.count()
    
    # 숙소 리뷰 관련 쿼리 추가
    accommodation_reviews = AccommodationReview.objects.filter(
        user=user
    ).order_by('-created_at')
    review_count = accommodation_reviews.count()
    
    # 동행 태그 처리
    for accompany in user_accompany:
        accompany.tags = accompany.tags.split(',') if accompany.tags else []
    
    return render(request, 'mypage/userDetail.html', {
        'user': user,
        'current_user': current_user,
        'plans': user_plans,
        'accompanies': user_accompany,
        'accompany_count': accompany_count,
        'accommodation_reviews': accommodation_reviews,  # 숙소 리뷰 데이터 추가
        'review_count': review_count,  # 리뷰 개수 추가
    })

@login_required
def plan_detail(request, pk):
    travel_plan = TravelPlan.objects.get(plan_id=pk)
    return render(request, 'mypage/plan_detail.html', {
        'travel_plan': travel_plan,
    })

def delete_trip(request, pk):
    travel_plan = TravelPlan.objects.get(plan_id=pk)
    travel_plan.delete()
    return redirect('users:my_trip')

def update_trip(request, pk):
    travel_plan = TravelPlan.objects.get(plan_id=pk)
    if request.method == 'POST':
        form = TravelPlanForm(request.POST, instance=travel_plan)
        if form.is_valid():
            travel_plan = form.save(commit=False)
            travel_plan.created_by = request.user
            travel_plan.save()
            return redirect('users:my_trip')
    else:
        form = TravelPlanForm(instance=travel_plan)
    return render(request, 'mypage/myTrip.html', {
        'form': form,
    })