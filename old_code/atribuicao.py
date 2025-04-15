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
from models.tbl_processos import TblProcessos
import logging
import traceback
from datetime import datetime

# Configurar o caminho para o Tesseract usando raw string para evitar problemas com barras invertidas
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Definir o caminho para a pasta de templates
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

nest_asyncio.apply()
load_dotenv()

# Obtém as credenciais do ambiente
senha_padrao = os.getenv("PASS", "")

# Configuração de logging
def setup_logging():
    """Configura o sistema de logging"""
    # Cria o diretório de logs se não existir
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Nome do arquivo de log com timestamp
    log_filename = f'logs/atribuicao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Configuração do logging
    logger = logging.getLogger('atribuicao')
    logger.setLevel(logging.INFO)
    
    # Remove handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    return logger

# Inicializa o logger
logger = setup_logging()

# Função de login
async def login(page, email, senha):
    """
    Realiza o processo de login no sistema
    
    Args:
        page: Página do navegador
        email (str): Email do usuário
        senha (str): Senha do usuário
    """
    try:
        logging.info(f"Realizando login para o usuário {email}")
        
        # Navega para a página de login
        await page.goto("https://braworkflowprod.service-now.com/", wait_until="networkidle")
        
        # Aguarda a página carregar completamente
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_load_state("networkidle")
        
        # Espera os campos ficarem disponíveis e visíveis
        await page.wait_for_selector('#userNameInput', state="visible", timeout=30000)
        await page.wait_for_selector('#passwordInput', state="visible", timeout=30000)
        
        # Limpa os campos antes de preencher
        await page.fill('#userNameInput', '', timeout=15000)
        await page.fill('#passwordInput', '', timeout=15000)
        
        # Preenche os campos com delay entre cada caractere
        await page.type('#userNameInput', email, delay=20)
        await page.type('#passwordInput', senha, delay=20)
        
        # Espera o botão ficar disponível e visível
        await page.wait_for_selector('#submitButton', state="visible", timeout=30000)
        
        # Clica no botão de submit
        await page.click('#submitButton')
        
        # Aguarda a navegação completar
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(10000)  # Aumentado para 10 segundos
        
        logging.info(f"Login realizado com sucesso para o usuário {email}")
        
    except Exception as e:
        logging.error(f"Erro ao realizar login para o usuário {email}: {str(e)}")
        logging.error(f"Traceback completo: {traceback.format_exc()}")
        raise

# Função de navegação pelo menu (usa "Favoritos" e "Solicitações - Grupo")
async def navegar_menu(page):
    print("Navegando no menu...")
    await page.wait_for_selector('div[role="button"]:has-text("Todos")', timeout=15000)
    await page.click('div[role="button"]:has-text("Todos")')
    await page.wait_for_timeout(1000)
    
    # digitar "Solicitações do(s)"
    await page.keyboard.type("Solicitações do(s)")
    
    await page.wait_for_selector('span:has-text("Solicitações do(s)")', timeout=15000)
    await page.click('span:has-text("Solicitações do(s)")')
    # await page.wait_for_timeout(300000)
    print("Menu navegado.")

# Função para preencher o campo GCPJ via OpenCV (usa o template "input_filtro_gcpj_grupo.png")
async def preencher_gcpj(page, gcpj):
    print("Preenchendo campo GCPJ via OpenCV...")
    screenshot_path = os.path.join(TEMPLATES_DIR, "screenshot.png")
    await page.screenshot(path=screenshot_path, full_page=True)
    print(f"Screenshot capturada e salva em: {screenshot_path}")

    img = cv2.imread(screenshot_path)
    template = cv2.imread(os.path.join(TEMPLATES_DIR, "input_filtro_gcpj_grupo.png"))
    
    if img is None:
        raise Exception("Erro ao carregar a screenshot.")
    if template is None:
        raise Exception("Erro ao carregar o template 'input_filtro_gcpj_grupo.png'. Verifique se o arquivo existe no caminho correto.")

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
    print(f"Elemento GCPJ encontrado em: x={center_x:.0f}, y={center_y:.0f}")
    
    await page.mouse.move(center_x, center_y)
    await page.mouse.click(center_x, center_y)
    print("Clique realizado no elemento GCPJ via OpenCV.")
    
    await page.wait_for_timeout(1000)
    await page.keyboard.type(gcpj, delay=50)
    await page.wait_for_timeout(1000)
    await page.keyboard.press("Enter")
    print("Valor preenchido e Enter pressionado no campo GCPJ.")

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
        screenshot_path = os.path.join(TEMPLATES_DIR, "screenshot.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot capturada e salva em: {screenshot_path}")
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
        screenshot_path = os.path.join(TEMPLATES_DIR, "screenshot.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot capturada e salva em: {screenshot_path}")
    
        # Carrega a screenshot e o template com OpenCV
        img = cv2.imread(screenshot_path)
        template_path = os.path.join(TEMPLATES_DIR, template_filename)
        template = cv2.imread(template_path)
        if img is None:
            raise Exception(f"Erro ao carregar a screenshot de {screenshot_path}.")
        if template is None:
            raise Exception(f"Erro ao carregar o template '{template_filename}' de {template_path}. Verifique se o arquivo existe.")
    
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

# Função para clicar no avatar do usuário e fazer logout
async def deslogar(page, email_usuario):
    """
    Realiza o processo de logout do usuário
    
    Args:
        page: Página do navegador
        email_usuario (str): Email do usuário
    """
    try:
        logging.info(f"Realizando logout para o usuário {email_usuario}")
        
        # Aguarda o avatar do usuário ficar visível
        await page.wait_for_selector(f'span.now-avatar-content:has-text("{email_usuario}")', timeout=30000)
        
        # Clica no avatar do usuário
        await page.click(f'span.now-avatar-content:has-text("{email_usuario}")')
        
        # Aguarda o menu de logout aparecer
        await page.wait_for_selector('button:has-text("Logout")', timeout=15000)
        
        # Clica no botão de logout
        await page.click('button:has-text("Logout")')
        
        # Aguarda a página de login
        await page.wait_for_selector('input[type="text"]', timeout=15000)
        
        logging.info(f"Logout realizado com sucesso para o usuário {email_usuario}")
        
    except Exception as e:
        logging.error(f"Erro ao realizar logout para o usuário {email_usuario}: {str(e)}")
        logging.error(f"Traceback completo: {traceback.format_exc()}")
        raise

async def atribuir_processos(page, usuario):
    """
    Atribui os processos pendentes de um usuário
    
    Args:
        page: Página do Playwright
        usuario (str): Email do usuário
    """
    try:
        logging.info(f"Atribuindo processos para o usuário {usuario}")
        
        # Obtém processos não atribuídos
        processos = TblProcessos.processos_nao_atribuidos_por_usuario(usuario)
        logging.info(f"Encontrados {len(processos)} processos para atribuir")
        
        for processo in processos:
            try:
                logging.info(f"Processando GCPJ: {processo.gcpj}")
                
                # Preenche o campo GCPJ
                await preencher_gcpj(page, processo.gcpj)
                
                # Clica no botão SAJ
                await click_text(page, "SAJ", timeout=15, interval=1)
                
                # Clica no botão de atribuir
                await clicar_por_template(page, "btn_atribuir_para_mim.png", threshold=0.8)
                await page.wait_for_timeout(3000)
                
                # Atualiza o status do processo
                if TblProcessos.atualizar_status_processo(processo, atribuido=True):
                    logging.info(f"Processo {processo.gcpj} atribuído com sucesso para {usuario}")
                else:
                    logging.error(f"Erro ao atribuir processo {processo.gcpj} para {usuario}")
                    
            except Exception as e:
                logging.error(f"Erro ao atribuir o processo {processo.gcpj}: {str(e)}")
                logging.error(f"Traceback completo: {traceback.format_exc()}")
                continue
                
    except Exception as e:
        logging.error(f"Erro ao atribuir processos do usuário {usuario}: {str(e)}")
        logging.error(f"Traceback completo: {traceback.format_exc()}")
        raise

# Função principal
async def run(usuario=None, processos=None):
    """
    Função principal que executa o processo de atribuição
    
    Args:
        usuario (str, optional): Email do usuário. Se None, processa todos os usuários com processos pendentes.
        processos (list, optional): Lista de processos para atribuir. Se None, busca processos pendentes do usuário.
    """
    try:
        logging.info(f"Iniciando processo de atribuição para usuário: {usuario}")
        
        # Verifica se a senha está disponível
        if not senha_padrao:
            logging.error("Senha não encontrada no arquivo .env")
            return
            
        # Inicializa o Playwright
        playwright_instance = await async_playwright().start()
        
        # Inicializa o navegador
        browser = await playwright_instance.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Realiza login
            await login(page, usuario, senha_padrao)
            
            # Navega até a página de atribuição
            await navegar_menu(page)
            
            # Processa os processos
            if usuario and processos:
                logging.info(f"Processando {len(processos)} processos para o usuário {usuario}")
                for processo in processos:
                    try:
                        await atribuir_processos(page, usuario)
                        logging.info(f"Processo {processo} atribuído com sucesso")
                    except Exception as e:
                        logging.error(f"Erro ao processar processo {processo}: {str(e)}")
                        logging.error(f"Traceback completo: {traceback.format_exc()}")
            else:
                # Lista usuários com processos pendentes
                usuarios = await listar_usuarios_pendentes(page)
                logging.info(f"Encontrados {len(usuarios)} usuários com processos pendentes")
                
                for usuario in usuarios:
                    try:
                        await atribuir_processos(page, usuario)
                        logging.info(f"Processos do usuário {usuario} processados com sucesso")
                    except Exception as e:
                        logging.error(f"Erro ao processar processos do usuário {usuario}: {str(e)}")
                        logging.error(f"Traceback completo: {traceback.format_exc()}")
            
            # Realiza logout
            await deslogar(page, usuario)
            
        except Exception as e:
            logging.error(f"Erro durante o processo de atribuição: {str(e)}")
            logging.error(f"Traceback completo: {traceback.format_exc()}")
            
        finally:
            # Fecha o navegador
            await browser.close()
            # Para o Playwright
            await playwright_instance.stop()
            
    except Exception as e:
        logging.error(f"Erro ao inicializar o processo de atribuição: {str(e)}")
        logging.error(f"Traceback completo: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run())
