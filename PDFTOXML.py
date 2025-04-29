import streamlit as st
import fitz
from PIL import Image
import io
import zipfile
import pandas as pd

def imagem_para_zpl(imagem_pb):
    width, height = imagem_pb.size
    pixels = imagem_pb.load()
    zpl_data = ""
    for y in range(height):
        byte = 0
        bits_filled = 0
        linha = ""
        for x in range(width):
            if pixels[x, y] == 0:
                byte |= (1 << (7 - bits_filled))
            bits_filled += 1
            if bits_filled == 8:
                linha += f"{byte:02X}"
                byte = 0
                bits_filled = 0
        if bits_filled > 0:
            linha += f"{byte:02X}"
        zpl_data += linha + "\n"

    bytes_per_row = (width + 7) // 8
    total_bytes = bytes_per_row * height
    zpl = (
        f"^XA\n"
        f"^PW{width}\n"
        f"^LL{height}\n"
        f"^FO0,0^GFA,{total_bytes},{total_bytes},{bytes_per_row},\n{zpl_data}^FS\n"
        f"^XZ"
    )
    return zpl

# ========== STREAMLIT APP ==========
st.set_page_config(page_title="Conversor Múltiplo PDF → ZPL", layout="centered")
st.title("🖨️ Conversor de PDFs para ZPL")
st.write("Faça upload de **um ou mais PDFs** e visualize as etiquetas geradas, com download dos ZPLs.")

uploaded_files = st.file_uploader("📄 Selecione os arquivos PDF", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    zpl_files = {}
    imagens_geradas = {}
    status_processamento = []

    # Processa todos os PDFs antes de mostrar qualquer coisa
    for uploaded_file in uploaded_files:
        nome_base = uploaded_file.name.rsplit('.', 1)[0]
        try:
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap(dpi=203)
                imagem = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            imagem_gray = imagem.convert("L")
            threshold = 180
            imagem_pb = imagem_gray.point(lambda x: 0 if x < threshold else 255, mode='1')

            max_width = 800
            if imagem_pb.width > max_width:
                ratio = max_width / imagem_pb.width
                new_height = int(imagem_pb.height * ratio)
                imagem_pb = imagem_pb.resize((max_width, new_height))

            zpl_resultado = imagem_para_zpl(imagem_pb)

            # Armazena resultados
            zpl_files[f"{nome_base}.zpl"] = zpl_resultado
            imagens_geradas[nome_base] = imagem_pb
            status_processamento.append({"Arquivo": uploaded_file.name, "Status": "✅ Sucesso"})

        except Exception as e:
            status_processamento.append({"Arquivo": uploaded_file.name, "Status": f"❌ Erro: {e}"})

    # ZIP logo no topo
    if zpl_files:
        st.divider()
        st.subheader("📦 Baixar todos os ZPLs juntos")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for nome_arquivo, conteudo_zpl in zpl_files.items():
                zip_file.writestr(nome_arquivo, conteudo_zpl)
        zip_buffer.seek(0)
        st.download_button(
            label="📥 Baixar ZIP com todos os ZPLs",
            data=zip_buffer,
            file_name="etiquetas_zpl.zip",
            mime="application/zip"
        )

    # Exibição de etiquetas e botões individuais
    for nome_arquivo_zpl, zpl in zpl_files.items():
        nome_base = nome_arquivo_zpl.rsplit('.', 1)[0]
        st.divider()
        st.subheader(f"Etiqueta: {nome_base}.pdf")

        st.image(imagens_geradas.get(nome_base), caption="Etiqueta Gerada", use_container_width=False)

        st.download_button(
            label="📥 Baixar ZPL",
            data=zpl.encode("utf-8"),
            file_name=f"{nome_base}.zpl",
            mime="text/plain"
        )

        with st.expander("🔍 Ver conteúdo do ZPL"):
            st.code(zpl, language="zpl")

    # Relatório
    st.divider()
    st.subheader("📊 Relatório de Processamento")
    df_status = pd.DataFrame(status_processamento)
    st.dataframe(df_status, use_container_width=True)
