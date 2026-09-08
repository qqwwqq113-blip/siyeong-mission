# 시영의 반짝 미션

시영이가 여러 가지 목표를 재미있게 진행하는 미션·선물 앱입니다. 영어 단어 100점, 일찍 일어나기, 문제집 완주처럼 원하는 미션을 부모님 확인 모드에서 자유롭게 만들고 별을 적립할 수 있습니다.

미션을 완성하면 선물 보물상자에서 선물을 **하나만** 고르는 팝업이 열립니다. 선물을 고른 미션은 새 라운드로 다시 시작할 수 있습니다.

## 실행

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

앱 데이터는 `data/app_data.json`에 저장됩니다. 기존 단어 도장판 데이터는 처음 실행할 때 자동으로 영어 단어 미션으로 옮겨집니다. 효과음은 선택 사항이며 MP3 파일을 `assets/sounds/`에 `stamp.mp3`, `celebration.mp3` 이름으로 넣으면 사용할 수 있습니다.

## 태블릿용 웹 배포

Streamlit Cloud에 `SUPABASE_URL`, `SUPABASE_KEY`, `APP_PASSWORD` 비밀값을 설정하면 Supabase에 기록을 저장합니다. 이 경우 컴퓨터가 꺼져 있어도 같은 웹주소에서 사용할 수 있습니다. 비밀값 형식은 `.streamlit/secrets.example.toml`을 참고하며, 실제 키가 담긴 `secrets.toml`은 GitHub에 올리지 않습니다.
