from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.conf import settings
from .models import User, UserReport
import requests
from django.core.files.storage import FileSystemStorage
import json
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import render, get_object_or_404
from .models import User, TravelPlan, TravelSchedule
from accompany.models import Accompany_Zzim, TravelParticipants, TravelGroup, AccompanyRequest
from flash.models import FlashZzim, Flash, FlashParticipants
from .serializers import SignupSerializer, UserSerializer, LoginSerializer
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, TravelPlanForm
from django.core.files.base import ContentFile
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from accommodation.models import AccommodationReview
from django.http import JsonResponse
from django.template.loader import render_to_string
from market.models import Market,MarketZzim
from .models import PhoneVerification
import qrcode
import random, string, io, base64, re, imaplib, email
from email.header import decode_header
from datetime import datetime, timedelta

@csrf_exempt
def get_csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})

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
    if not user.is_active:
        return render(request, 'mypage/account_suspended.html', {'error': '계정 이용이 정지되었습니다.'})
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
    if not user.is_active:
        return render(request, 'mypage/account_suspended.html', {'error': '계정 이용이 정지되었습니다.'})
    
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
                login(request, user)
                request.session.save()
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
                request.session.save()
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

            if User.objects.filter(email=email).exists():
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': '이미 존재하는 이메일입니다.'})
                else:
                    return render(request, 'register/register.html', {'error': '이미 존재하는 이메일입니다.'})
            
            # 전화번호 중복 체크
            if not phone:
                # 전화번호 값이 없으면
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': '전화번호를 입력하세요.'})
                else:
                    return render(request, 'register/register.html', {'error': '전화번호를 입력하세요.'})
            elif User.objects.filter(user_phone=phone).exists():
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': '이미 존재하는 전화번호입니다.'})
                else:
                    return render(request, 'register/register.html', {'error': '이미 존재하는 전화번호입니다.'})


            #  성별 값 변환 (default: 'U' Unknown)
            gender_map = {"male": "M", "female": "F"}
            user_gender = gender_map.get(gender, "U")

            # 닉네임 기본값 설정
            if not nickname:
                nickname = name or "사용자"

            # 생년월일 설정
            if birth_year and birth_month and birth_day:
                birth = f"{birth_year}-{birth_month}-{birth_day}"
            else:
                birth = None  # 기본값 설정 가능

            # 나이 계산 (예외 방지)
            try:
                from datetime import datetime
                current_year = datetime.now().year
                user_age = current_year - int(birth_year) if birth_year.isdigit() else None
            except Exception as e:
                print(f"⚠️ 나이 계산 오류: {e}")
                user_age = None

            # 사용자 생성
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

            # 프로필 이미지 저장
            if profile_image:
                user.profile_image = profile_image
            else:
                user.profile_image = 'profile_images/default-profile.png'  # 기본 프로필 지정

            user.save()
            print(f"✅ 회원가입 성공: {user.email}")

            # 회원가입 후 자동 로그인
            login(request, user)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect_url': f"{request.build_absolute_uri('/')}"} )
            else:
                return redirect('main:home')

        except Exception as e:
            print(f"❌ 회원가입 중 오류 발생: {e}") 
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            else:
                context = {
                    'error': str(e),
                    'email': email,
                    'name': name,
                    'nickname': nickname,
                    'birth-year': birth_year,
                    'birth-month': birth_month,
                    'birth-day': birth_day,
                    'phone': phone,
                    'gender': gender,
                }
                return render(request, 'register/register.html', context)
    return render(request, 'register/register.html')



def user_logout(request):
    logout(request)
    return redirect('main:home')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_active:
                # 계정이 정지된 경우
                return render(request, 'account_suspended.html', {'error': '계정 이용이 정지되었습니다.'})
            else:
                # 세션에 로그인 처리 (Django의 세션 인증)
                login(request, user)

                # JWT 토큰 발급 (API용)
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)

                return redirect('main:home')
        else:
            return render(request, 'login/login.html', {'error': '로그인 실패'})
    return render(request, 'login/login.html')


# 마이페이지 설정
@login_required
def my_page(request):
    return render(request, 'mypage/myPage.html', {'user':request.user})

# 랜덤 문자열 생성 함수
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def get_decoded_header(header_value):
    decoded_parts = decode_header(header_value)
    header_text = ""
    for part, encoding in decoded_parts:
        # 인코딩이 None이거나 'unknown-8bit'인 경우 대체 인코딩 사용
        if encoding is None or (isinstance(encoding, str) and encoding.lower() == 'unknown-8bit'):
            encoding = 'utf-8'
        if isinstance(part, bytes):
            try:
                header_text += part.decode(encoding, errors="replace")
            except Exception as e:
                # 만약 여전히 에러가 난다면, 기본 utf-8로 디코딩
                header_text += part.decode('utf-8', errors="replace")
        else:
            header_text += part
    return header_text

def phone_verification(request):
    # 새로운 랜덤 문자열을 생성
    random_str = generate_random_string(10)
    PhoneVerification.objects.create(
        user=request.user if request.user.is_authenticated else None,
        random_string=random_str
    )

    request.session['phone_verification_code'] = random_str
    sms_link = f"sms:piro.urabi@gmail.com?body={random_str}"
    
    # QR 코드 생성 
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(sms_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    context = {
        'random_str': random_str,
        'sms_link': sms_link,
        'qr_code_base64': qr_code_base64,
    }
    return render(request, 'register/phone_verification.html', context)


def search_email_for_code(mail, random_str):
    # 먼저 INBOX에서 검색
    result, data = mail.search(None, f'(BODY "{random_str}")')
    if data[0]:
        return data[0].split()
    # 만약 INBOX에 없으면 스팸 폴더
    mail.select('[Gmail]/Spam')  
    result, data = mail.search(None, f'(BODY "{random_str}")')
    if data[0]:
        return data[0].split()
    return None

def verify_phone_status(request):
    random_str = request.session.get('phone_verification_code')
    if not random_str:
        return JsonResponse({'result': 'unauthorized'})
    
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        mail.select('inbox')
        result, data = mail.search(None, f'(BODY "{random_str}")')
        if not data[0]:
            return JsonResponse({'result': 'wait'})
        
        email_ids = data[0].split()
        result, msg_data = mail.fetch(email_ids[-1], '(RFC822)')
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # 디코딩된 From 헤더 사용
        raw_from_header = msg.get('From', '')
        from_header = get_decoded_header(raw_from_header)
        print("DECODED FROM HEADER:", from_header)
        
        # 전화번호 추출
        match = re.search(r'(0\d{9,10})', from_header)
        if match:
            phone_number = match.group(1)
            verification_obj = PhoneVerification.objects.filter(random_string=random_str).latest('created_at')
            verification_obj.verified = True
            verification_obj.phone_number = phone_number
            verification_obj.save()
            if request.user.is_authenticated:
                request.user.user_phone = phone_number
                request.user.save()
            return JsonResponse({'result': 'verified', 'phone_number': phone_number})
        return JsonResponse({'result': 'wait'})
    except Exception as e:
        print("Verification error:", e)
        return JsonResponse({'result': 'error'})

# 정보 수정
@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)

        birth_year = request.POST.get("birth_year")
        birth_month = request.POST.get("birth_month")
        birth_day = request.POST.get("birth_day")

        if 'profile_image' in request.FILES:
            print("파일 업로드 감지됨!")
        else:
            print("파일 업로드가 안 됨")
        if birth_year and birth_month and birth_day:
            request.user.birth = f"{birth_year}-{birth_month}-{birth_day}" 

        if form.is_valid():
            form.save()
            request.user.save() 
            return redirect('users:my_page')
        else:
            print(form.errors) 
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'mypage/editProfile.html', {'form': form, 'user': request.user})


def check_phone_duplicate(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone = data.get("phone")

        clean_phone = re.sub(r'\D', '', phone)

        print(f" [DEBUG] 중복 검사 요청 받은 전화번호: {clean_phone}")

        existing_user = User.objects.filter(user_phone__isnull=False).exclude(user_phone="").exclude(id=request.user.id).filter(user_phone=clean_phone).first()
        
        if existing_user:
            request.user.user_phone = None
            request.user.save()
            print(f"[DEBUG] 중복된 전화번호 발견: {existing_user.user_phone}")
            print(f"[DEBUG] 중복된 전화번호 발견: {existing_user.email}")
            return JsonResponse({
                "success": False, 
                "error": "이미 존재하는 전화번호입니다.",
                "server_phone": existing_user.user_phone
            })

        print(f"[DEBUG] 사용 가능한 전화번호: {clean_phone}")
        return JsonResponse({
            "success": True,
            "phone": clean_phone
        })

# 채팅 : 토큰 발급
@login_required
def get_token_for_logged_in_user(request):
    refresh = RefreshToken.for_user(request.user)
    return JsonResponse({
        "access": str(refresh.access_token)
    })

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def some_protected_route(request):
    return Response({'message': 'This is a protected route!'}, status=status.HTTP_200_OK)
@login_required
def my_trip(request, pk):
    this_schedule = get_object_or_404(TravelSchedule, schedule_id=pk)
    date_list = []
    current_date = this_schedule.start_date
    while current_date <= this_schedule.end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)
    plan_id_str = request.GET.get('plan_id')
    if plan_id_str:
        try:
            travel_plan = TravelPlan.objects.get(plan_id=plan_id_str)
        except TravelPlan.DoesNotExist:
            travel_plan = None
    else:
        travel_plan = None

    plan_date_str = request.GET.get('plan_date')
    if plan_date_str:
        try:
            selected_date = datetime.strptime(plan_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = this_schedule.start_date
    else:
        if travel_plan:
            selected_date = travel_plan.start_date
        else:
            selected_date = this_schedule.start_date

    if request.method == 'POST':
        post_plan_id = request.POST.get('plan_id')
        if post_plan_id:
            try:
                travel_plan = TravelPlan.objects.get(plan_id=post_plan_id)
            except TravelPlan.DoesNotExist:
                travel_plan = None

        # 새로 선택된 날짜(드롭다운-hidden)
        post_date_str = request.POST.get('plan_date','')
        if post_date_str:
            try:
                selected_date = datetime.strptime(post_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        if travel_plan:
            form = TravelPlanForm(request.POST, instance=travel_plan)
        else:
            form = TravelPlanForm(request.POST)

        if form.is_valid():
            saved_plan = form.save(commit=False)
            saved_plan.created_by = request.user
            saved_plan.schedule   = this_schedule
            saved_plan.start_date = selected_date
            saved_plan.end_date   = selected_date

            markers_json = request.POST.get('markers','[]')
            try:
                saved_plan.markers = json.loads(markers_json)
            except json.JSONDecodeError:
                saved_plan.markers = []

            polyline_json = request.POST.get('polyline','[]')
            try:
                saved_plan.polyline = json.loads(polyline_json)
            except json.JSONDecodeError:
                saved_plan.polyline = []
            saved_plan.save()
            return redirect('users:schedule_detail', pk=this_schedule.schedule_id)
        else:
            print("폼 에러:", form.errors)

    else:
        if travel_plan:
            form = TravelPlanForm(instance=travel_plan) # 수정
        else:
            form = TravelPlanForm() # 새로 생성

    context = {
        'this_schedule': this_schedule,
        'date_list': date_list,
        'selected_date': selected_date,
        'form': form,
        'travel_plan': travel_plan, 
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
        
    }
    return render(request, 'mypage/myTrip.html', context)


@login_required
def user_detail(request, pk):
    user = get_object_or_404(User, id=pk)
    current_user = request.user  
    
    # 여행 계획 및 동행 관련 쿼리 작성 
    user_plans = TravelPlan.objects.filter(created_by=user)
    user_accompany = TravelGroup.objects.filter(created_by=user)
    accompany_count = user_accompany.count()
    
    # 숙소 리뷰 쿼리 수정 - is_parent=False인 리뷰만 가져오기
    accommodation_reviews = AccommodationReview.objects.filter(
        user=user,
        is_parent=False
    ).order_by('-created_at')
    
    review_count = accommodation_reviews.count()
    #나눔마켓
    mkt_self_items = Market.objects.filter(user=user)
    mkt_self_count = mkt_self_items.count()

    # 사용자가 등록한 번개 모임 가져오기
    flash_meetings = Flash.objects.filter(created_by=user).order_by("-date_time")
    flash_count = flash_meetings.count()

    for accompany in user_accompany:
        accompany.tags = accompany.tags.split(',') if accompany.tags else []
    
    return render(request, 'mypage/userDetail.html', {
        'user': user,
        'current_user': current_user,
        'plans': user_plans,
        'accompanies': user_accompany,
        'accompany_count': accompany_count,
        "flash_meetings": flash_meetings,
        "flash_count": flash_count,
        'accommodation_reviews': accommodation_reviews,  # 숙소 리뷰 데이터 추가 
        'review_count': review_count,  # 리뷰 개수 추가
        'has_more': review_count > 5,  # 더보기 버튼 표시 여부
        'mkt_self_items' :mkt_self_items, #마켓 작성자 게시글
        'mkt_self_count' :mkt_self_count,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })
    

@login_required
def plan_detail(request, pk):
    travel_plan = TravelPlan.objects.get(plan_id=pk)
    return render(request, 'mypage/plan_detail.html', {
        'travel_plan': travel_plan,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })

def delete_trip(request, pk):
    travel_plan = TravelPlan.objects.get(plan_id=pk)
    travel_plan.delete()
    return redirect('users:schedule_detail', pk=travel_plan.schedule.schedule_id)

@login_required
def update_trip(request, pk):
    travel_plan = get_object_or_404(TravelPlan, plan_id=pk)
    this_schedule = travel_plan.schedule

    # 스케줄 기간에 해당하는 date_list 생성
    date_list = []
    current = this_schedule.start_date
    while current <= this_schedule.end_date:
        date_list.append(current)
        current += timedelta(days=1)
    plan_date_str = request.GET.get('plan_date')
    if plan_date_str:
        try:
            selected_date = datetime.strptime(plan_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = travel_plan.start_date
    else:
        selected_date = travel_plan.start_date

    if request.method == 'POST':
        form = TravelPlanForm(request.POST, instance=travel_plan)
        if form.is_valid():
            updated_plan = form.save(commit=False)
            post_date_str = request.POST.get('plan_date', '')
            if post_date_str:
                try:
                    new_date = datetime.strptime(post_date_str, "%Y-%m-%d").date()
                except ValueError:
                    new_date = travel_plan.start_date 
            else:
                new_date = travel_plan.start_date

            updated_plan.start_date = new_date
            updated_plan.end_date = new_date
            markers_str = request.POST.get('markers', '[]')
            try:
                updated_plan.markers = json.loads(markers_str)
            except json.JSONDecodeError:
                updated_plan.markers = []
            
            polyline_str = request.POST.get('polyline', '[]')
            try:
                updated_plan.polyline = json.loads(polyline_str)
            except json.JSONDecodeError:
                updated_plan.polyline = []

            updated_plan.save()
            return redirect('users:plan_detail', pk=updated_plan.plan_id)
        else:
            print("폼 에러:", form.errors)
    else:
        form = TravelPlanForm(instance=travel_plan)

    context = {
        'this_schedule': this_schedule,
        'form': form,
        'date_list': date_list,
        'selected_date': selected_date,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'mypage/myTrip.html', context)


def user_list(request):
    user = get_object_or_404(User, id=request.user.id)
    user_schedules = TravelSchedule.objects.filter(user=user).order_by('-created_at')
    schedule_count = user_schedules.count()
    for schedule in user_schedules:
        schedule.plans_count = TravelPlan.objects.filter(schedule=schedule).count()
    
    user_accompanies = TravelParticipants.objects.filter(user=user)
    accompany_items = []
    for participate in user_accompanies:
        travel_group = TravelGroup.objects.get(travel_id=participate.travel_id)
        travel_group.tags = travel_group.tags.split(',') if travel_group.tags else []
        if travel_group.markers:
            try:
                markers = json.loads(travel_group.markers)
                processed_markers = [marker for marker in markers if marker.get("title")]
                travel_group.markers = processed_markers[:3]
            except json.JSONDecodeError:
                travel_group.markers = []
        else:
            travel_group.markers = []
        # 만약 제목이나 markers가 없으면 승인되지 않은 것
        if travel_group.title and travel_group.markers:
            accompany_items.append(travel_group)
    accompany_count = len(accompany_items)
    
    user_request = AccompanyRequest.objects.filter(user=user)
    user_request_count = user_request.count()

    flash_participants = FlashParticipants.objects.filter(user=user).select_related('flash')
    flash_participant_count = flash_participants.count()

    return render(request, 'mypage/planlist.html', {
        'user' : user,
        'schedules': user_schedules,
        'schedule_count': schedule_count,
        'accompanies': accompany_items,  
        'accompany_count': accompany_count,
        'ac_requests': user_request,
        'flash_participants': [fp.flash for fp in flash_participants],
        'flash_participant_count': flash_participant_count,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })


def zzim_list(request):
    user = get_object_or_404(User, id=request.user.id)

    ac_zzims = Accompany_Zzim.objects.filter(user=user)
    ac_zzim_items = []
    for zzim in ac_zzims:
        item = zzim.item  # 동행 글 객체
        if item.markers:
            try:
                markers = json.loads(item.markers)
                item.markers = [marker for marker in markers if marker.get("title")][:3]
            except json.JSONDecodeError:
                item.markers = []
        else:
            item.markers = []
        ac_zzim_items.append(item)

            
    ac_zzim_count = ac_zzims.count()

    flash_zzims = FlashZzim.objects.filter(user=user).select_related("flash")
    flash_zzim_items = [zzim.flash for zzim in flash_zzims]
    flash_zzim_count = flash_zzims.count()

    acc_zzims = AccommodationReview.objects.filter(favorites=user) \
                  .exclude(accommodation_name="") \
                  .exclude(city="")
    acc_zzim_count = acc_zzims.count()
    
    mkt_zzims = MarketZzim.objects.filter(user=user)
    mkt_zzims_items = [zzim.market for zzim in mkt_zzims]
    mkt_zzim_count = mkt_zzims.count()

    return render(request, 'mypage/zzim_list.html', {
        'ac_zzims': ac_zzim_items,
        'ac_zzim_count': ac_zzim_count,
        'flash_zzims': flash_zzim_items,
        'flash_zzim_count': flash_zzim_count,
        'mkt_zzims': mkt_zzims_items,
        'mkt_zzim_count' : mkt_zzim_count,
        'acc_zzims': acc_zzims,
        'acc_zzim_count': acc_zzim_count,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })


def schedule_create(request):
    if request.method == 'POST':
        schedule_name = request.POST.get('title')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        new_schedule = TravelSchedule.objects.create(name=schedule_name, user=request.user, start_date=start_date, end_date=end_date)
        return redirect('users:schedule_detail', pk=new_schedule.schedule_id)
    
@login_required
def schedule_detail(request, pk):
    schedule = get_object_or_404(TravelSchedule, schedule_id=pk)
    travel_plans = TravelPlan.objects.filter(schedule=schedule).order_by('start_date')
    return render(request, 'mypage/schedule_detail.html', {
        'schedule': schedule,
        'travel_plans': travel_plans,
    })


def delete_schedule(request):
    schedule_id = request.GET.get('schedule_id')
    schedule = get_object_or_404(TravelSchedule, pk=schedule_id)
    schedule.delete()
    return redirect('users:user_list')


def update_schedule_photo(request):
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        photo_file  = request.FILES.get('photo')
        schedule = get_object_or_404(TravelSchedule, pk=schedule_id)
        if photo_file:
            schedule.photo = photo_file
            schedule.save()
        return redirect('users:schedule_detail', pk=schedule_id)
    return redirect('users:my_page')


@login_required
def report_user(request, user_id):
    if request.method == 'POST':
        reported_user = get_object_or_404(User, pk=user_id)
        
        if UserReport.objects.filter(reporter=request.user, reported=reported_user).exists():
            return JsonResponse({'error': '이미 신고하셨습니다.'}, status=400)
        
        UserReport.objects.create(reporter=request.user, reported=reported_user)
        
        if reported_user.reports_received.count() >= 3:
            reported_user.is_active = False
            reported_user.save()
        
        return JsonResponse({'message': '신고되었습니다.'})
    
    return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

def account_suspended(request):
    return render(request, 'account_suspended.html', {'error': '계정 이용이 정지되었습니다.'})
