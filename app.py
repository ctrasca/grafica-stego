import streamlit as st
from PIL import Image
import numpy as np
import io

# Configurare pagina
st.set_page_config(
    page_title="Steganografie LSB - Proiect Grafica",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def text_to_binary(text):
    """
    Converteste un text (string) intr-un sir binar.
    Fiecare caracter este transformat in 8 biti (ASCII/UTF-8).
    """
    binary_data = ''.join(format(ord(char), '08b') for char in text)
    return binary_data

def binary_to_text(binary_data):
    """
    Converteste un sir binar inapoi in text.
    Grupeaza bitii cate 8 pentru a reconstrui caracterele.
    """
    all_bytes = [binary_data[i: i+8] for i in range(0, len(binary_data), 8)]
    decoded_text = ""
    for byte in all_bytes:
        decoded_text += chr(int(byte, 2))
    return decoded_text

def encode_lsb(image, message):
    """
    Ascunde mesajul in imaginea data folosind metoda LSB.
    Returneaza imaginea modificata sau None daca mesajul e prea lung.
    """
    # Adaugam delimitatorul specificat pentru a sti unde se termina mesajul la decodificare
    message += "#####"
    
    img_array = np.array(image)
    
    # Verificam capacitatea imaginii
    # Imaginea are width * height pixeli, fiecare pixel are 3 canale (RGB) care pot stoca info
    # (ignoram Alpha daca exista pentru simplificare sau il tratam separat, dar uzual LSB se face pe RGB)
    max_bytes = img_array.shape[0] * img_array.shape[1] * 3 // 8
    if len(message) > max_bytes:
        st.error(f"E prea lung textul, sefu'! Mai taie din el. Maxim caractere: {max_bytes}")
        return None

    binary_message = text_to_binary(message)
    data_len = len(binary_message)
    data_index = 0
    
    # Iteram prin pixeli si modificam LSB
    # img_array este (height, width, channels)
    # Ne asiguram ca lucram pe o copie pentru a nu altera originalul in memorie gresit
    encrypted_img_array = img_array.copy()
    
    rows, cols, channels = encrypted_img_array.shape
    
    # Flatten la array pentru iterare mai usoara, apoi reshape la final
    flat_img = encrypted_img_array.flatten()
    
    for i in range(len(flat_img)):
        if data_index < data_len:
            # Preluam bitul curent din mesaj
            bit = int(binary_message[data_index])
            
            # Modificam LSB-ul valorii curente a pixelului
            # Golim ultimul bit cu & 254 (11111110) si adaugam bitul mesajului
            flat_img[i] = (flat_img[i] & 254) | bit
            
            data_index += 1
        else:
            break
            
    # Reconstituim forma imaginii
    encrypted_img_array = flat_img.reshape(rows, cols, channels)
    return Image.fromarray(encrypted_img_array.astype('uint8'))

def decode_lsb(image):
    """
    Extrage mesajul ascuns din imagine.
    Se opreste cand intalneste delimitatorul "#####".
    """
    img_array = np.array(image)
    flat_img = img_array.flatten()
    
    binary_data = ""
    delimiter = "#####"
    
    # Extragem LSB din fiecare valoare de culoare
    for value in flat_img:
        binary_data += str(value & 1)
        
        # Verificam periodic daca am gasit delimitatorul (la fiecare octet format)
        if len(binary_data) >= 8 and len(binary_data) % 8 == 0:
            # Convertim ce am gasit pana acum in text pentru a cauta delimitatorul
            # Aceasta este o optimizare pentru a nu parcurge toti pixelii inutil
            current_text = binary_to_text(binary_data)
            if delimiter in current_text:
                return current_text.split(delimiter)[0] # Returnam doar mesajul, fara delimitator
    
    # Daca am parcurs toata imaginea si nu am gasit delimitatorul
    return None

# --- Interfata Grafica (UI) ---

st.title("🎨 Steganografie LSB")
st.markdown("""
Poti sa ascunzi mesaje secrete in poze si sa nu le vada nimeni.
Folosim metoda **LSB** (modificam ultimul bit din pixel), deci poza o sa arate la fel.
""")

tab1, tab2 = st.tabs(["🔒 Ascunde Mesaj", "🔓 Citeste Mesaj"])

# --- TAB 1: ENCODE ---
with tab1:
    st.header("Bagam un mesaj intr-o poza")
    
    uploaded_file = st.file_uploader("Alege o poza (merge JPG sau PNG)", type=["jpg", "jpeg", "png"], key="upload_encode")
    user_text = st.text_area("Ce vrei sa scrii secret?", placeholder="Mesajul tau secret...")
    
    if uploaded_file and user_text:
        image = Image.open(uploaded_file).convert("RGB") # Convertim la RGB
        st.image(image, caption="Asta e poza ta originala", width=300)
        
        if st.button("Ascunde-l!"):
            with st.spinner("Acum lucrez..."):
                result_image = encode_lsb(image, user_text)
                
            if result_image:
                st.success("Gata! Mesajul e ascuns.")
                st.image(result_image, caption="Asa arata acum (identic, nu?)", width=300)
                
                # Pregatim imaginea pentru download
                buf = io.BytesIO()
                result_image.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="📥 Descarca Poza Secreta",
                    data=byte_im,
                    file_name="poza_cu_secret.png",
                    mime="image/png",
                    help="Trebuie PNG ca sa nu se strice mesajul (lossless)."
                )

# --- TAB 2: DECODE ---
with tab2:
    st.header("Hai sa vedem ce scrie")
    
    decode_file = st.file_uploader("Pune poza aia cu mesaj (doar PNG)", type=["png"], key="upload_decode")
    
    if decode_file:
        stego_image = Image.open(decode_file).convert("RGB")
        st.image(stego_image, caption="Poza incarcata", width=300)
        
        if st.button("Oare ce zice"):
            with st.spinner("Caut biti ascunsi..."):
                decoded_text = decode_lsb(stego_image)
                
            if decoded_text:
                st.success("Bingo! Am gasit ceva:")
                st.markdown(f"**Mesajul secret este:**")
                st.code(decoded_text)
            else:
                st.warning("N-am gasit nimic... Esti sigur ca poza asta are mesaj in ea?")
