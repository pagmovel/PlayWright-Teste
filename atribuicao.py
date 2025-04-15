import os
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
    await page.fill('#userNameInput', usuario)
    await page.fill('#passwordInput', senha)
    await page.click('#submitButton')
    await page.wait_for_timeout(7000)
    print("Login realizado.")

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
    template = cv2.imread("input_filtro_item_grupo.png")
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
    await page.wait_for_timeout(1000)
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


# Nova função: clicar_por_template()
# Essa função recebe o nome do arquivo do template que deve ser localizado e clicado.
async def clicar_por_template(page, template_filename, threshold=0.8, timeout=15, interval=1):
    """
    Tira uma screenshot da página, utiliza OpenCV para localizar o template especificado e clica nele.
    Aguarda até que o template seja encontrado ou até que o timeout seja atingido.

    :param page: objeto page do Playwright.
    :param template_filename: nome do arquivo de imagem do template (ex: "meu_template.png").
    :param threshold: valor mínimo para considerar uma correspondência válida.
    :param timeout: tempo máximo de espera em segundos.
    :param interval: intervalo de verificação entre tentativas, em segundos.
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
        template = cv2.imread(template_filename)
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
            await page.mouse.move(center_x, center_y)
            await page.mouse.click(center_x, center_y)
            print(f"Clique realizado no elemento utilizando o template '{template_filename}'.")
            return  # Encerra a função após o clique
    
        if time.time() - start_time > timeout:
            raise Exception(f"Timeout: Template '{template_filename}' não encontrado na screenshot após {timeout} segundos.")
    
        await asyncio.sleep(interval)

# Função principal
async def run():
    async with async_playwright() as p:
        # Inicia o navegador em modo anônimo (incognito) e sem viewport para usar o tamanho real da janela
        browser = await p.chromium.launch(headless=False, args=["--incognito"])
        context = await browser.new_context(viewport=None)
        page = await context.new_page()
        
        await login(page)
        await navegar_menu(page)
        # Preenche o campo item com o valor "2201043253"
        await preencher_item(page, "2201043253")
        # Usa a função genérica para clicar em um elemento cujo texto inicia com "SAJ" via OCR
        await click_text(page, "SAJ", timeout=15, interval=1)
        # Exemplo de uso da nova função: clicar em um elemento cujo template está no arquivo "meu_template.png"
        # Apenas descomente a linha abaixo se desejar testar essa funcionalidade:
        print("Localizando")
        await clicar_por_template(page, "btn_atribuir_para_mim.png", threshold=0.8)
        
        # Aguarda para visualização ou interação final
        await page.wait_for_timeout(300000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
