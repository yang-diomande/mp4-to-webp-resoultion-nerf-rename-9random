import streamlit as st
import tempfile
import os
import subprocess
import random
import base64

st.set_page_config(page_title="MP4 to WebP 일괄 변환기 (랜덤 파일명)", page_icon="🖼️", layout="centered")

st.title("🖼️ 양의 WEBP 변환기")
st.write("랜덤인 숫자 10자리 파일명으로 도출되며 화질 너프, 일괄 다운로드 진행 가능")
st.write("여러 MP4 파일을 선택하면 일괄 변환하며 다운로드할 수 있습니다.")

# 세션 상태 초기화
if "converted_files" not in st.session_state:
    st.session_state.converted_files = []
if "download_trigger" not in st.session_state:
    st.session_state.download_trigger = False

# 여러 파일 선택 지원
uploaded_files = st.file_uploader(
    "", 
    type=["mp4"], 
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if uploaded_files:
    st.info(f"📁 총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    
    if st.button("🔄 WEBP로 전체 변환 시작", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        temp_dir = tempfile.mkdtemp()
        st.session_state.converted_files = []
        st.session_state.download_trigger = False

        # 앞자리 '1' 뒤에 오는 9자리 랜덤 시작 번호 생성 (100000000 ~ 999999999)
        start_rand_num = random.randint(100000000, 999999999)

        for idx, uploaded_file in enumerate(uploaded_files):
            current_num = start_rand_num + idx
            
            # 9자리 범위를 넘어가면 오버플로우 처리
            if current_num > 999999999:
                current_num = 100000000 + (current_num - 1000000000)
                
            # 맨 앞 '1' 고정 + 9자리 순차/랜덤 번호 조합 (총 10자리)
            output_name = f"1{current_num}.webp"

            status_text.text(f"⏳ [{idx + 1}/{len(uploaded_files)}] 변환 중: {uploaded_file.name} ➔ {output_name}")
            
            tmp_input_path = os.path.join(temp_dir, uploaded_file.name)
            with open(tmp_input_path, "wb") as f:
                f.write(uploaded_file.read())

            output_path = os.path.join(temp_dir, output_name)

            try:
                cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', tmp_input_path,
                    '-vcodec', 'libwebp',
                    # 💡 가로/세로 비율 고정 없이 원본 크기의 일정 비율(약 41.6%)만큼 화질/해상도만 균등하게 축소
                    '-filter:v', 'scale=iw*0.416:ih*0.416,fps=fps=min(source_fps\,30)',
                    '-lossless', '0',
                    '-q:v', '53',
                    '-preset', 'default',
                    '-loop', '0',
                    output_path
                ]
                
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    with open(output_path, "rb") as f:
                        file_bytes = f.read()
                    file_size_mb = round(len(file_bytes) / (1024 * 1024), 2)
                    
                    st.session_state.converted_files.append((output_name, uploaded_file.name, file_bytes, file_size_mb))

            except Exception as e:
                st.error(f"❌ {uploaded_file.name} 변환 실패: {e}")

            progress_bar.progress((idx + 1) / len(uploaded_files))

        status_text.empty()
        progress_bar.empty()

# 변환 결과 출력 (항상 유지)
if st.session_state.converted_files:
    st.success(f"🔮 총 {len(st.session_state.converted_files)}개 파일 변환 완료!")
    st.markdown("---")
    
    st.subheader("📦 전체 일괄 다운로드")
    
    if st.button("⚡ 변환된 WebP 전체 한 번에 다운로드", use_container_width=True, type="secondary"):
        st.session_state.download_trigger = True

    # 일괄 다운로드 자바스크립트 실행 (0.3초 간격)
    if st.session_state.download_trigger:
        js_code = "<script>\n"
        for idx, (output_name, _, file_bytes, _) in enumerate(st.session_state.converted_files):
            b64 = base64.b64encode(file_bytes).decode()
            js_code += f"""
            setTimeout(function() {{
                var a = document.createElement('a');
                a.href = 'data:image/webp;base64,{b64}';
                a.download = '{output_name}';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }}, {idx * 300});
            """
        js_code += "</script>"
        st.components.v1.html(js_code, height=1, width=1)
        st.session_state.download_trigger = False  # 실행 후 트리거 리셋

    st.markdown("---")
    st.subheader("📥 개별 다운로드 목록")

    for idx, (output_name, orig_name, file_bytes, file_size_mb) in enumerate(st.session_state.converted_files):
        st.write(f"**{idx + 1}. {output_name}** (원본: `{orig_name}` / {file_size_mb} MB)")
        st.download_button(
            label=f"📥 {output_name} 다운로드",
            data=file_bytes,
            file_name=output_name,
            mime="image/webp",
            key=f"rand_download_{idx}_{output_name}",
            use_container_width=True
        )
