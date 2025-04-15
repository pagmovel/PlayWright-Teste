import os
import re
from dotenv import load_dotenv
import nest_asyncio
import asyncio
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from time import sleep
from playwright.async_api import async_playwright

# Configurar o caminho para o Tesseract usando raw string para evitar problemas com barras invertidas
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

nest_asyncio.apply()
load_dotenv()
usuario = os.getenv("USER")
senha = os.getenv("PASS")

# Função de login
async def login(page):
    print("Realizando login...")
    await page.goto("https://braworkflowprod.service-now.com/")
    
    # Espera os campos ficarem disponíveis
    await page.wait_for_selector('#userNameInput', timeout=15000)
    await page.wait_for_selector('#passwordInput', timeout=15000)
    
    # Preenche os campos
    await page.fill('#userNameInput', usuario, timeout=15000)
    await page.fill('#passwordInput', senha, timeout=15000)
    
    # Espera o botão ficar disponível e clica
    await page.wait_for_selector('#submitButton', timeout=15000)
    await page.click('#submitButton')

# Função de navegação pelo menu (usa "Favoritos" e "Solicitações - Grupo")
async def navegar_menu(page):
    print("Navegando no menu...")
    await page.wait_for_selector('div[role="button"]:has-text("Favoritos")', timeout=15000)
    await page.click('div[role="button"]:has-text("Favoritos")')
    await page.wait_for_selector('span:has-text("Solicitações - Grupo")', timeout=15000)
    await page.click('span:has-text("Solicitações - Grupo")')
    await page.wait_for_timeout(3000)
    print("Menu navegado.")

# Função para preencher o campo item via OpenCV (usa o template "input_filtro_item_grupo.png")
async def preencher_item(page, item):
    print("Preenchendo campo item via OpenCV...")
    screenshot_path = "screenshot.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    print("Screenshot capturada.")

    img = cv2.imread(screenshot_path)
    template = cv2.imread("templates/input_filtro_item_grupo.png")
    if img is None:
        raise Exception("Erro ao carregar a screenshot.")
    if template is None:
        raise Exception("Erro ao carregar o template 'input_filtro_item_grupo.png'. Verifique se o arquivo existe no caminho correto.")

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8  # Ajuste esse valor se necessário
    loc = np.where(res >= threshold)
    points = list(zip(*loc[::-1]))
    
    if not points:
        raise Exception("Template não encontrado na screenshot.")
    
    x, y = points[0]
    h, w = template_gray.shape
    center_x = x + w / 2
    center_y = y + h / 2
    print(f"Elemento item encontrado em: x={center_x:.0f}, y={center_y:.0f}")
    
    await page.mouse.move(center_x, center_y)
    await page.mouse.click(center_x, center_y)
    print("Clique realizado no elemento item via OpenCV.")
    
    await page.wait_for_timeout(1000)
    await page.keyboard.type(item, delay=50)
    # await page.wait_for_timeout(1000)
    await page.keyboard.press("Enter")
    print("Valor preenchido e Enter pressionado no campo item.")

# Função genérica para esperar que um texto fique visível via OCR e clicar nele
async def click_text(page, texto, timeout=15, interval=1):
    """
    Aguarda até que um elemento cujo texto inicie com 'texto' seja encontrado via OCR e clica nele.
    :param page: objeto page do Playwright.
    :param texto: string que deve iniciar o texto do elemento.
    :param timeout: tempo máximo de espera em segundos.
    :param interval: intervalo de verificação em segundos.
    """
    print(f"Aguardando que o texto que inicia com '{texto}' fique visível...")
    import time
    start_time = time.time()
    
    while True:
        screenshot_path = "screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        img = cv2.imread(screenshot_path)
        if img is None:
            raise Exception("Erro ao carregar a screenshot para OCR.")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ocr_data = pytesseract.image_to_data(gray, output_type=Output.DICT, lang='por')
        n_boxes = len(ocr_data['level'])
        target_box = None
        
        for i in range(n_boxes):
            t = ocr_data['text'][i].strip()
            if t.startswith(texto):
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                target_box = (x, y, w, h)
                print(f"Texto encontrado: '{t}' em {target_box}")
                break
        
        if target_box:
            x, y, w, h = target_box
            center_x = x + w / 2
            center_y = y + h / 2
            print(f"Elemento localizado em: x={center_x:.0f}, y={center_y:.0f}")
            await page.mouse.move(center_x, center_y)
            await page.mouse.click(center_x, center_y)
            print(f"Clique realizado no elemento que inicia com '{texto}' via OCR.")
            return
        
        if time.time() - start_time > timeout:
            raise Exception(f"Timeout: o texto que inicia com '{texto}' não ficou visível em {timeout} segundos.")
        
        await asyncio.sleep(interval)


# # Nova função: clicar_por_template()
# # Essa função recebe o nome do arquivo do template que deve ser localizado e clicado.
# async def clicar_por_template(page, template_filename, threshold=0.8, timeout=15, interval=1):
#     """
#     Tira uma screenshot da página, utiliza OpenCV para localizar o template especificado e clica nele.
#     Aguarda até que o template seja encontrado ou até que o timeout seja atingido.

#     :param page: objeto page do Playwright.
#     :param template_filename: nome do arquivo de imagem do template (ex: "meu_template.png").
#     :param threshold: valor mínimo para considerar uma correspondência válida.
#     :param timeout: tempo máximo de espera em segundos.
#     :param interval: intervalo de verificação entre tentativas, em segundos.
#     """
#     print(f"Localizando elemento usando o template '{template_filename}'...")
#     import time
#     start_time = time.time()
    
#     while True:
#         screenshot_path = "screenshot.png"
#         await page.screenshot(path=screenshot_path, full_page=True)
#         print("Screenshot capturada.")
    
#         # Carrega a screenshot e o template com OpenCV
#         img = cv2.imread(screenshot_path)
#         template = cv2.imread(template_filename)
#         if img is None:
#             raise Exception("Erro ao carregar a screenshot.")
#         if template is None:
#             raise Exception(f"Erro ao carregar o template '{template_filename}'. Verifique se o arquivo existe.")
    
#         # Converte as imagens para escala de cinza
#         img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
#         # Aplica template matching para localizar o template na screenshot
#         res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
#         loc = np.where(res >= threshold)
#         points = list(zip(*loc[::-1]))
    
#         if points:
#             x, y = points[0]
#             h, w = template_gray.shape
#             center_x = x + w / 2
#             center_y = y + h / 2
#             print(f"Elemento encontrado com o template '{template_filename}' em: x={center_x:.0f}, y={center_y:.0f}")
#             await page.mouse.move(center_x, center_y)
#             await page.mouse.click(center_x, center_y)
#             print(f"Clique realizado no elemento utilizando o template '{template_filename}'.")
#             return  # Encerra a função após o clique
    
#         if time.time() - start_time > timeout:
#             raise Exception(f"Timeout: Template '{template_filename}' não encontrado na screenshot após {timeout} segundos.")
    
#         await asyncio.sleep(interval)

async def clicar_por_template(page, template_filename, threshold=0.8, timeout=15, interval=1, delay=0.2, enter=False, texto=None):
    """
    Tira uma screenshot da página, utiliza OpenCV para localizar o template especificado e clica nele.
    Aguarda até que o template seja encontrado ou até que o timeout seja atingido.

    :param page: objeto page do Playwright.
    :param template_filename: nome do arquivo de imagem do template (ex: "meu_template.png").
    :param threshold: valor mínimo para considerar uma correspondência válida.
    :param timeout: tempo máximo de espera em segundos.
    :param interval: intervalo de verificação entre tentativas, em segundos.
    :param delay: tempo de espera em segundos após posicionar o mouse antes de clicar (default: 0.5s).
    """
    print(f"Localizando elemento usando o template '{template_filename}'...")
    import time
    start_time = time.time()
    
    while True:
        screenshot_path = "screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print("Screenshot capturada.")
    
        # Carrega a screenshot e o template com OpenCV
        img = cv2.imread(screenshot_path)
        template = cv2.imread(f"templates/{template_filename}")
        if img is None:
            raise Exception("Erro ao carregar a screenshot.")
        if template is None:
            raise Exception(f"Erro ao carregar o template '{template_filename}'. Verifique se o arquivo existe.")
    
        # Converte as imagens para escala de cinza
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
        # Aplica template matching para localizar o template na screenshot
        res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        points = list(zip(*loc[::-1]))
    
        if points:
            x, y = points[0]
            h, w = template_gray.shape
            center_x = x + w / 2
            center_y = y + h / 2
            print(f"Elemento encontrado com o template '{template_filename}' em: x={center_x:.0f}, y={center_y:.0f}")
            
            # Posiciona o mouse no elemento encontrado
            await page.mouse.move(center_x, center_y)
            # Aguarda o delay definido antes de clicar
            await asyncio.sleep(delay)
            
            if texto:
                # Se um texto for fornecido, digita o texto
                await page.keyboard.type(texto, delay=10)
                print(f"Texto '{texto}' digitado.")
                await page.keyboard.press("Enter")
                
                return  # Encerra a função após o clique
            
            if enter:
                # Se enter for True, simula o pressionamento da tecla Enter após o clique
                await page.keyboard.press("Enter")
                print(f"Tecla Enter realizado no elemento utilizando o template '{template_filename}'.")
            elif not enter:
                # Realiza o clique
                await page.mouse.click(center_x, center_y)
                print(f"Clique realizado no elemento utilizando o template '{template_filename}'.")
                
            
            

            return  # Encerra a função após o clique
    
        if time.time() - start_time > timeout:
            raise Exception(f"Timeout: Template '{template_filename}' não encontrado na screenshot após {timeout} segundos.")
    
        await asyncio.sleep(interval)

async def digitar_valores(page, valor, delay=50, sleep_time=0.5):
    # Em sistemas Windows/Linux (Ctrl+A)
    await asyncio.sleep(sleep_time)
    await page.keyboard.down('Control')
    await page.keyboard.press('A')
    await page.keyboard.up('Control')
    
    # Digitar o valor da contra proposta, removendo R$, espaços e pontos.
    padrao = r'(R\$|\s|\.)'
    contra_tratado = re.sub(padrao, '', valor)
    await page.keyboard.type(contra_tratado, delay=delay)


# Função principal
async def run():
    async with async_playwright() as p:
        # Inicia o navegador em modo anônimo (incognito) e sem viewport para usar o tamanho real da janela
        browser = await p.chromium.launch(headless=False, args=["--incognito"])
        context = await browser.new_context(viewport=None)
        page = await context.new_page()
        
        await login(page)
        
        dados = [
            {"item": "2500031070", "contra": "R$     5.000,00", "fase": "Pré-sentença", "base":"Limite", "alcada":"R$     2.542,00"},
            {"item": "2400784841", "contra": "R$     4.000,00", "fase": "Pré-sentença", "base":"Limite", "alcada":"R$     2.542,00"},
            {"item": "2400740532", "contra": "R$     8.000,00", "fase": "Pré-sentença", "base":"Limite", "alcada":"R$     2.542,00"},
            {"item": "2300073848", "contra": "R$     5.000,00", "fase": "Pré-sentença", "base":"Limite", "alcada":"R$     2.542,00"},
            {"item": "2500052914", "contra": "R$     4.000,00", "fase": "Pré-sentença", "base":"Limite", "alcada":"R$     2.542,00"},
        ]
        
        for dado in dados:
            await navegar_menu(page)
            print(dado['item'])
            # Preenche o campo item com o valor 
            await preencher_item(page, dado["item"])
            # Usa a função genérica para clicar em um elemento cujo texto inicia com "SAJ" via OCR
            await click_text(page, "SAJ", timeout=15, interval=1)
            # Exemplo de uso da nova função: clicar em um elemento cujo template está no arquivo "meu_template.png"

            
            # aqui fazer try para validar se já foi atrubuido ou não
            # await clicar_por_template(page, "btn_atribuir_para_mim.png", threshold=0.8)
            
            #clicar no select tipo sentença
            await clicar_por_template(page, "select_tipo_sentenca.png", threshold=0.8, timeout=15, interval=1)
            
            if dado['fase'] == "Pré-sentença":
                # await clicar_por_template(page, "option_pre_sentenca.png", threshold=0.9, timeout=15, interval=1)
                # Simula a tecla seta para baixo
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
            else:
                # await clicar_por_template(page, "option_pos_sentenca.png", threshold=0.8, timeout=15, interval=1)
                pass
            
            
            # Mover o foco para fora do input
            await clicar_por_template(page, "mover_foco_label_controle_sentenca.png", threshold=0.8, timeout=15, interval=1)
            
            # rolar a pagina para baixo para visuallizar o select Astatus Acordo
            await page.keyboard.press("PageDown")
            sleep(1)
            
            # clica no select Status Acordo
            await clicar_por_template(page, "select_status_acordo.png", threshold=0.8, timeout=15, interval=1)
            
            sleep(1)
            # Digitar Solicitar Aprovação Banco no select Status Acordo
            await clicar_por_template(page, "option_solicitar_aprovacao_banco.png", threshold=0.8, timeout=15, interval=1, delay=1, texto="solicitar")
            
            # clica no input Valor Contra proposta
            await clicar_por_template(page, "input_contra_proposta.png", threshold=0.8, timeout=15, interval=1)
            
            # Preencher o valor da contra proposta
            await digitar_valores(page, dado["contra"], delay=50)

            # Clicar no botão Atualizar
            await clicar_por_template(page, "btn_atualizar_valor.png", threshold=0.8, timeout=15, interval=1, delay=1)
        
            
            
            
            # Aguarda para visualização ou interação final
            await page.wait_for_timeout(5000)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
