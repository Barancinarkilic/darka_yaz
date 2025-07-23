import json
import streamlit as st
from airtable import Airtable

# ——— Load Airtable creds from JSON ———
with open("secrets.json", "r", encoding="utf-8") as f:
    creds = json.load(f)

API_KEY    = creds["airtable_api_key"]
BASE_ID    = creds["airtable_base_id"]
TABLE_NAME = creds.get("table_name", "Registrations")

airtable = Airtable(BASE_ID, TABLE_NAME, API_KEY)

# ——— Streamlit page setup ———
st.set_page_config(page_title="Event Kayıt", layout="wide")

# ——— Confirmation overlay if “id” query‑param is present ———
params = st.query_params
if "id" in params:
    record_number = params["id"]

    st.markdown(f"""
    <style>
      /* Full-screen, fixed overlay using flex so text+number stay together */
      .stOverlay {{
        position: fixed !important;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: #f9f9f9;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 1rem;
        overflow-y: auto;
        z-index: 9999;
      }}
      .stOverlay h2 {{
        color: #222 !important;           /* force a dark color */
        font-size: 1.6rem !important;
        line-height: 1.3 !important;
        margin: 0 0 1rem 0 !important;
      }}
      .stOverlay h1 {{
        color: #d9534f !important;
        font-size: 5rem !important;
        margin: 0 !important;
      }}
      @media (max-width: 480px) {{
        .stOverlay h2 {{ font-size: 1.2rem !important; }}
        .stOverlay h1 {{ font-size: 4rem !important; }}
      }}
    </style>
    <div class="stOverlay">
      <h2>
        Bu numarayı aklınızda tutmanız veya ekran görüntüsünü almanız<br>
        giriş esnasında bizi çok hızlandıracaktır.<br>
        Lütfen kaybetmeyiniz.
      </h2>
      <h1>{record_number}</h1>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ——— Otherwise: show registration form ———
st.title("Event Kayıt Formu")

# ——— Session state init ———
if 'guest_count' not in st.session_state:
    st.session_state.guest_count = 0
if 'misafir_durumu_onceki' not in st.session_state:
    st.session_state.misafir_durumu_onceki = "Hayır"

# ——— Participant details ———
isim_soyisim = st.text_input("İsim Soyisim *")
yas          = st.number_input("Yaşınız *", min_value=1, max_value=120, step=1)

# ——— Phone number section (18 % / 82 %) ———
st.markdown("### Telefon Numarası *")
phone_cols = st.columns([0.18, 0.82])
with phone_cols[0]:
    ulke_kodu = st.text_input(
        "Ülke Kodu",
        value="+90",
        max_chars=4,
        help="Lütfen ülke kodunu (örn. +90) giriniz",
        label_visibility="visible"
    )
with phone_cols[1]:
    telefon_numarasi = st.text_input(
        "Telefon Numarası",
        max_chars=10,
        placeholder="5XX XXX XX XX",
        help="10 haneli telefon numarasını giriniz",
        label_visibility="visible"
    )

# ——— Club‑member & guest toggle ———
darka_uye      = st.radio("Darka Spor Kulübü Üyesi misiniz? *", ("Evet", "Hayır"), horizontal=True)
misafir_var_mi = st.radio(
    "Misafir/Çocuklarınızla mı katılıyorsunuz? * (Form dolduracak misafir/çocuklarınızı girmeyiniz.)",
    ("Evet", "Hayır"),
    horizontal=True,
    index=1
)

# clear guest entries if toggled off
if misafir_var_mi == "Hayır" and st.session_state.misafir_durumu_onceki == "Evet":
    for i in range(st.session_state.guest_count):
        for suffix in ("isim", "yas"):
            st.session_state.pop(f"guest_{i}_{suffix}", None)
    st.session_state.guest_count = 0
st.session_state.misafir_durumu_onceki = misafir_var_mi

# ——— Guest details ———
if misafir_var_mi == "Evet":
    st.subheader("Misafir/Çocuk Bilgileri")
    add_col, rem_col, _ = st.columns([0.15, 0.15, 0.7])
    with add_col:
        if st.button("➕ Ekle", use_container_width=True):
            st.session_state.guest_count += 1
    with rem_col:
        if st.button("➖ Sil", use_container_width=True, disabled=st.session_state.guest_count == 0):
            idx = st.session_state.guest_count - 1
            for suffix in ("isim", "yas"):
                st.session_state.pop(f"guest_{idx}_{suffix}", None)
            st.session_state.guest_count = idx

    for i in range(st.session_state.guest_count):
        g1, g2 = st.columns([0.6, 0.4])
        with g1:
            st.text_input(f"Misafir {i+1} İsim Soyisim", key=f"guest_{i}_isim")
        with g2:
            st.number_input(
                f"Misafir {i+1} Yaş",
                min_value=0,
                max_value=120,
                step=1,
                key=f"guest_{i}_yas"
            )

# ——— Submit button ———
st.markdown("---")
if st.button("Kaydı Tamamla"):
    # validation
    if not isim_soyisim or not telefon_numarasi or not yas:
        st.error("Lütfen tüm zorunlu alanları doldurun.")
    elif len(telefon_numarasi) != 10 or not telefon_numarasi.isdigit():
        st.error("Lütfen geçerli bir telefon numarası girin.")
    else:
        # build guest list
        guest_list = []
        if misafir_var_mi == "Evet":
            for i in range(st.session_state.guest_count):
                name = st.session_state.get(f"guest_{i}_isim", "").strip()
                age  = st.session_state.get(f"guest_{i}_yas", 0)
                if name:
                    guest_list.append({"isim": name.lower(), "yas": age})

        # prepare record
        record = {
            "isim_soyisim":    isim_soyisim,
            "yas":             yas,
            "telefon_numarasi": f"{ulke_kodu}{telefon_numarasi}",
            "darka_uyesi":     darka_uye,
            "misafir_durumu":  misafir_var_mi,
            "misafirler":      json.dumps(guest_list, ensure_ascii=False)
        }

        try:
            result   = airtable.insert(record)
            auto_num = result["fields"].get("id")
            if auto_num is None:
                st.error("Airtable’dan 'id' alanı alınamadı.")
            else:
                st.query_params["id"] = str(auto_num)
                st.rerun()
        except Exception as e:
            st.error(f"Airtable’a yazarken hata oluştu: {e}")
