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
params = st.experimental_get_query_params()
if "id" in params:
    # Extract the first value (query_params gives a list)
    record_number = params["id"][0]

    # Inline styles only—no <style> tag or media queries
    overlay_html = f"""
    <div style="
        position: fixed !important;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: rgba(249,249,249,1);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 1rem;
        overflow-y: auto;
        z-index: 9999;
    ">
      <h2 style="
          color: #222 !important;
          font-size: 1.6rem !important;
          line-height: 1.3 !important;
          margin: 0 0 1rem 0 !important;
      ">
        Bu numarayı aklınızda tutmanız veya ekran görüntüsünü almanız<br>
        giriş esnasında bizi çok hızlandıracaktır.<br>
        Lütfen kaybetmeyiniz.
      </h2>
      <h1 style="
          color: #d9534f !important;
          font-size: 5rem !important;
          margin: 0 !important;
      ">
        {record_number}
      </h1>
    </div>
    """
    st.markdown(overlay_html, unsafe_allow_html=True)
    st.stop()

# ——— Otherwise: form page ———
st.title("Event Kayıt Formu")

# ——— Session state init ———
st.session_state.setdefault('guest_count', 0)
st.session_state.setdefault('misafir_durumu_onceki', "Hayır")

# ——— Participant details ———
isim_soyisim = st.text_input("İsim Soyisim *")
yas          = st.number_input("Yaşınız *", min_value=1, max_value=120, step=1)

# ——— Phone number section ———
st.subheader("Telefon Numarası *")
phone_cols = st.columns([0.18, 0.82])
with phone_cols[0]:
    ulke_kodu = st.text_input(
        "Ülke Kodu",
        value="+90",
        max_chars=4,
        help="Lütfen ülke kodunu (örn. +90) giriniz"
    )
with phone_cols[1]:
    telefon_numarasi = st.text_input(
        "Telefon Numarası",
        max_chars=10,
        placeholder="5XX XXX XX XX",
        help="10 haneli telefon numarasını giriniz"
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
    if add_col.button("➕ Ekle", use_container_width=True):
        st.session_state.guest_count += 1
    if rem_col.button("➖ Sil", use_container_width=True, disabled=st.session_state.guest_count == 0):
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
                min_value=0, max_value=120, step=1,
                key=f"guest_{i}_yas"
            )

# ——— Divider & Submit ———
st.divider()
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
            "isim_soyisim":     isim_soyisim,
            "yas":              yas,
            "telefon_numarasi": f"{ulke_kodu}{telefon_numarasi}",
            "darka_uyesi":      darka_uye,
            "misafir_durumu":   misafir_var_mi,
            "misafirler":       json.dumps(guest_list, ensure_ascii=False)
        }

        try:
            result   = airtable.insert(record)
            auto_num = result["fields"].get("id")
            if auto_num is None:
                st.error("Airtable’dan 'id' alanı alınamadı.")
            else:
                st.experimental_set_query_params(id=str(auto_num))
                st.rerun()
        except Exception as e:
            st.error(f"Airtable’a yazarken hata oluştu: {e}")
