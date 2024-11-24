import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# API 설정
API_URL = "http://newly-liberal-mammal.ngrok-free.app/api"
TOKEN = None

class ResearchAssistantUI:
    def __init__(self):
        self.setup_session_state()

    def setup_session_state(self):
        if 'token' not in st.session_state:
            st.session_state.token = None
        if 'current_project' not in st.session_state:
            st.session_state.current_project = None
        if 'show_signup' not in st.session_state:
            st.session_state.show_signup = False

    def signup_page(self):
        st.title("회원가입")
        with st.form("signup_form"):
            email = st.text_input("이메일")
            full_name = st.text_input("이름")
            password = st.text_input("비밀번호", type="password")
            password_confirm = st.text_input("비밀번호 확인", type="password")
            
            submitted = st.form_submit_button("회원가입")
            if submitted:
                if password != password_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                    return
                    
                data = {
                    "email": email,
                    "full_name": full_name,
                    "password": password
                }
                
                response = requests.post(
                    f"{API_URL}/users/",
                    json=data
                )
                
                if response.status_code == 201:
                    st.success("회원가입이 완료되었습니다! 로그인해주세요.")
                    st.session_state.show_signup = False
                else:
                    st.error(f"회원가입 실패: {response.json().get('detail', '알 수 없는 오류가 발생했습니다.')}")

    def login_page(self):
        st.title("Research Assistant Login")
        
        # 회원가입 버튼
        if not st.session_state.show_signup:
            if st.button("회원가입"):
                st.session_state.show_signup = True
                st.experimental_rerun()
            
            # 로그인 폼
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")

                if submitted:
                    response = requests.post(
                        f"{API_URL}/token/",
                        data={"email": email, "password": password}
                    )
                    if response.status_code == 200:
                        st.session_state.token = response.json()['access']
                        st.success("로그인 성공!")
                        st.experimental_rerun()
                    else:
                        st.error("로그인 실패. 이메일과 비밀번호를 확인해주세요.")
        else:
            self.signup_page()
            if st.button("로그인으로 돌아가기"):
                st.session_state.show_signup = False
                st.experimental_rerun()

    def create_project(self):
        st.subheader("새 연구 프로젝트 생성")
        with st.form("create_project_form"):
            title = st.text_input("프로젝트 제목")
            description = st.text_area("프로젝트 설명")
            research_field = st.selectbox(
                "연구 분야",
                ["안보", "정치", "경제", "사회", "기술", "기타"]
            )
            evaluation_plan = st.text_area("평가 계획")
            
            submitted = st.form_submit_button("프로젝트 생성")
            if submitted:
                headers = {'Authorization': f'Bearer {st.session_state.token}'}
                data = {
                    'title': title,
                    'description': description,
                    'research_field': research_field,
                    'evaluation_plan': evaluation_plan
                }
                response = requests.post(
                    f"{API_URL}/research/",
                    headers=headers,
                    json=data
                )
                if response.status_code == 201:
                    st.success("프로젝트가 생성되었습니다!")
                    st.session_state.current_project = response.json()
                else:
                    st.error("프로젝트 생성 실패")

    def view_projects(self):
        st.subheader("내 연구 프로젝트")
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.get(f"{API_URL}/research/", headers=headers)
        
        if response.status_code == 200:
            projects = response.json()['results']
            if not projects:
                st.info("프로젝트가 없습니다.")
                return

            # 프로젝트 목록을 데이터프레임으로 표시
            df = pd.DataFrame(projects)
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
            df = df[['id', 'title', 'research_field', 'evaluation_status', 'created_at']]
            df.columns = ['ID', '제목', '연구분야', '상태', '생성일']
            st.dataframe(df)

            # 프로젝트 선택
            selected_id = st.selectbox(
                "프로젝트 선택",
                options=df['ID'].tolist(),
                format_func=lambda x: df[df['ID'] == x]['제목'].iloc[0]
            )

            if selected_id:
                self.view_project_detail(selected_id)

    def view_project_detail(self, project_id):
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.get(f"{API_URL}/research/{project_id}/", headers=headers)
        
        if response.status_code == 200:
            project = response.json()
            st.subheader(project['title'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**상태:**", project['evaluation_status'])
                st.write("**연구분야:**", project['research_field'])
                st.write("**진행률:**", f"{(project['completed_steps']/project['total_steps'])*100:.1f}%" if project['total_steps'] > 0 else "0%")
            
            with col2:
                if st.button("연구 실행"):
                    self.execute_research(project_id)
                if st.button("상태 확인"):
                    self.check_research_status(project_id)

            # 연구 단계 표시
            if 'research_steps' in project:
                st.subheader("연구 단계")
                for step in project['research_steps']:
                    with st.expander(f"Step {step['step_number']}: {step['description'][:50]}..."):
                        st.write("**상태:**", step['status'])
                        st.write("**진행률:**", f"{step['progress_percentage']}%")
                        if step['result']:
                            st.json(step['result'])

    def execute_research(self, project_id):
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.post(
            f"{API_URL}/research/{project_id}/execute/",
            headers=headers
        )
        if response.status_code == 200:
            st.success("연구가 시작되었습니다!")
        else:
            st.error("연구 시작 실패")

    def check_research_status(self, project_id):
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.get(
            f"{API_URL}/research/{project_id}/status/",
            headers=headers
        )
        if response.status_code == 200:
            status = response.json()
            st.write("**현재 상태:**", status['status'])
            st.progress(status['completed_steps'] / status['total_steps'])
            st.write(f"진행 단계: {status['completed_steps']}/{status['total_steps']}")
        else:
            st.error("상태 확인 실패")

    def view_subscription(self):
        st.subheader("구독 정보")
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.get(f"{API_URL}/subscriptions/current/", headers=headers)
        
        if response.status_code == 200:
            subscription = response.json()
            
            # 구독 정보 표시
            col1, col2 = st.columns(2)
            with col1:
                st.write("**플랜:**", subscription['plan_type'])
                st.write("**상태:**", subscription['status'])
                st.write("**만료일:**", subscription['end_date'])
            
            with col2:
                if subscription['status'] == 'ACTIVE':
                    if st.button("구독 취소"):
                        self.cancel_subscription(subscription['id'])
                else:
                    st.write("**신규 구독하기**")
                    self.subscribe_form()

            # 사용량 표시
            st.subheader("사용량")
            usage = subscription.get('current_usage', {})
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("프로젝트", f"{usage.get('projects_count', 0)}/{subscription['usage_limit']['max_projects']}")
            with col2:
                st.metric("참고문헌", f"{usage.get('references_count', 0)}/{subscription['usage_limit']['max_references']}")
            with col3:
                st.metric("LLM 요청", f"{usage.get('llm_requests_count', 0)}/{subscription['usage_limit']['max_llm_requests']}")
            with col4:
                st.metric("스토리지", f"{usage.get('storage_used_mb', 0)}/{subscription['usage_limit']['storage_limit_mb']} MB")

    def subscribe_form(self):
        # 구독 플랜 선택
        plan = st.selectbox(
            "구독 플랜 선택",
            ["BASIC", "PREMIUM", "ENTERPRISE"],
            format_func=lambda x: {
                "BASIC": "Basic (₩10,000/월)",
                "PREMIUM": "Premium (₩30,000/월)",
                "ENTERPRISE": "Enterprise (₩100,000/월)"
            }[x]
        )
        
        if st.button("구독하기"):
            self.process_subscription(plan)

    def process_subscription(self, plan_type: str):
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        
        # 결제 생성
        payment_data = {
            'plan_type': plan_type
        }
        response = requests.post(
            f"{API_URL}/payments/create/",
            headers=headers,
            json=payment_data
        )
        
        if response.status_code == 200:
            payment_info = response.json()
            
            # 결제 정보 표시
            st.write("**결제 정보**")
            st.write("금액:", payment_info['amount'])
            st.write("주문번호:", payment_info['order_id'])
            
            # 결제 처리
            if st.button("결제 진행"):
                payment_response = requests.post(
                    f"{API_URL}/payments/{payment_info['id']}/process/",
                    headers=headers
                )
                
                if payment_response.status_code == 200:
                    st.success("결제가 완료되었습니다!")
                    st.experimental_rerun()
                else:
                    st.error("결제 처리 중 오류가 발생했습니다.")
        else:
            st.error("결제 정보 생성 중 오류가 발생했습니다.")

    def cancel_subscription(self, subscription_id: int):
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.post(
            f"{API_URL}/subscriptions/{subscription_id}/cancel/",
            headers=headers
        )
        
        if response.status_code == 200:
            st.success("구독이 취소되었습니다.")
            st.experimental_rerun()
        else:
            st.error("구독 취소 중 오류가 발생했습니다.")

    def view_payment_history(self):
        st.subheader("결제 내역")
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        response = requests.get(f"{API_URL}/payments/", headers=headers)
        
        if response.status_code == 200:
            payments = response.json()['results']
            if not payments:
                st.info("결제 내역이 없습니다.")
                return

            # 결제 내역을 데이터프레임으로 표시
            df = pd.DataFrame(payments)
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
            df = df[['id', 'amount', 'status', 'created_at']]
            df.columns = ['ID', '금액', '상태', '결제일']
            st.dataframe(df)

            # 환불 요청
            if st.button("환불 요청"):
                selected_payment = st.selectbox(
                    "환불할 결제 선택",
                    options=df['ID'].tolist(),
                    format_func=lambda x: f"결제 {x} ({df[df['ID'] == x]['금액'].iloc[0]}원)"
                )
                
                reason = st.text_area("환불 사유")
                if st.button("환불 신청"):
                    self.request_refund(selected_payment, reason)

    def request_refund(self, payment_id: int, reason: str):
        headers = {'Authorization': f'Bearer {st.session_state.token}'}
        data = {
            'reason': reason
        }
        response = requests.post(
            f"{API_URL}/payments/{payment_id}/refund/",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            st.success("환불이 요청되었습니다.")
            st.experimental_rerun()
        else:
            st.error("환불 요청 중 오류가 발생했습니다.")

    def main(self):
        st.sidebar.title("Research Assistant")

        if not st.session_state.token:
            self.login_page()
            return

        menu = st.sidebar.selectbox(
            "메뉴",
            ["프로젝트 목록", "새 프로젝트 생성", "구독 관리", "결제 내역"]
        )

        if menu == "새 프로젝트 생성":
            self.create_project()
        elif menu == "프로젝트 목록":
            self.view_projects()
        elif menu == "구독 관리":
            self.view_subscription()
        elif menu == "결제 내역":
            self.view_payment_history()

        if st.sidebar.button("로그아웃"):
            st.session_state.token = None
            st.experimental_rerun()

if __name__ == "__main__":
    app = ResearchAssistantUI()
    app.main() 