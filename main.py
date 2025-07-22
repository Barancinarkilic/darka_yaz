import json
import datetime
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
st.set_page_config(page_title="Event Kayıt", layout="centered")
st.title("Event Kayıt Formu")

# ——— Session state for guests ———
if 'guest_count' not in st.session_state:
    st.session_state.guest_count = 0
if 'misafir_durumu_onceki' not in st.session_state:
    st.session_state.misafir_durumu_onceki = "Hayır"

# ——— Main form fields ———
isim_soyisim = st.text_input("İsim Soyisim *")
yas          = st.number_input("Yaşınız *", min_value=1, max_value=120, step=1)

st.write("Telefon Numarası *")
col1, col2 = st.columns([0.2, 0.8])
with col1:
    ulke_kodu = st.text_input("Ülke Kodu", value="+90", label_visibility="collapsed")
with col2:
    telefon_numarasi = st.text_input(
        "", max_chars=10, placeholder="5XX XXX XX XX", label_visibility="collapsed"
    )

darka_uye      = st.radio("Darka Spor Kulübü Üyesi misiniz? *", ("Evet", "Hayır"), horizontal=True)
misafir_var_mi = st.radio(
    "Misafir/Çocuklarınızla mı katılıyorsunuz? *",
    ("Evet", "Hayır"),
    horizontal=True,
    index=1
)

# ——— Clear guest entries if switched back to “Hayır” ———
if misafir_var_mi == "Hayır" and st.session_state.misafir_durumu_onceki == "Evet":
    for i in range(st.session_state.guest_count):
        for suffix in ("isim", "yas"):
            st.session_state.pop(f"guest_{i}_{suffix}", None)
    st.session_state.guest_count = 0

st.session_state.misafir_durumu_onceki = misafir_var_mi

# ——— Guest section ———
guest_list = []
if misafir_var_mi == "Evet":
    st.subheader("Misafir/Çocuk Bilgileri")
    btn_col1, btn_col2, _ = st.columns([0.15, 0.15, 0.7])
    with btn_col1:
        if st.button("➕ Ekle", use_container_width=True):
            st.session_state.guest_count += 1
    with btn_col2:
        if st.button(
            "➖ Sil",
            use_container_width=True,
            disabled=st.session_state.guest_count == 0
        ):
            idx = st.session_state.guest_count - 1
            for suffix in ("isim", "yas"):
                st.session_state.pop(f"guest_{idx}_{suffix}", None)
            st.session_state.guest_count = idx

    for i in range(st.session_state.guest_count):
        c1, c2 = st.columns([0.6, 0.4])
        with c1:
            st.text_input(f"Misafir {i+1} İsim Soyisim", key=f"guest_{i}_isim")
        with c2:
            st.number_input(
                f"Misafir {i+1} Yaş",
                min_value=0,
                max_value=120,
                step=1,
                key=f"guest_{i}_yas"
            )

# ——— Submission ———
st.markdown("---")
if st.button("Kaydı Tamamla"):
    # validation
    if not isim_soyisim or not telefon_numarasi or not yas:
        st.error("Lütfen tüm zorunlu alanları doldurun.")
    elif len(telefon_numarasi) != 10 or not telefon_numarasi.isdigit():
        st.error("Lütfen geçerli bir telefon numarası girin.")
    else:
        # build guest_list
        if misafir_var_mi == "Evet":
            guest_list = []
            for i in range(st.session_state.guest_count):
                name = st.session_state.get(f"guest_{i}_isim", "").strip()
                age  = st.session_state.get(f"guest_{i}_yas", 0)
                if name:
                    guest_list.append({"isim": name.lower(), "yas": age})

        # prepare Airtable record
        record = {
            "isim_soyisim":    isim_soyisim,
            "yas":             yas,
            "telefon_numarasi":         f"{ulke_kodu}{telefon_numarasi}",
            "darka_uyesi":     darka_uye,
            "misafir_durumu":  misafir_var_mi,
            "misafirler":      json.dumps(guest_list, ensure_ascii=False)
        }

        # write to Airtable using `create` (not `insert`)
        try:
            airtable.insert(record)    # <— note `.insert`
            st.success("Kaydınız başarıyla kaydedildi!")
        except Exception as e:
            st.error(f"Airtable’a yazarken hata oluştu: {e}")