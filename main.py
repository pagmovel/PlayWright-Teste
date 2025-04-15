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
from models.tbl_processos import TblProcessos
import logging
import traceback

# Configurar o caminho para o Tesseract usando raw string para evitar problemas com barras invertidas
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Definir o caminho para a pasta de templates
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

nest_asyncio.apply()
load_dotenv()
usuario = os.getenv("USER")
senha = os.getenv("PASS")

# Função de login
async def login(page, usuario):
    print("- Realizando login...")
    await page.goto("https://braworkflowprod.service-now.com/")
    await page.fill('#userNameInput', usuario)
    await page.fill('#passwordInput', senha)
    await page.click('#submitButton')
    await page.wait_for_timeout(5000)
    print("- Login realizado.")

# Função de navegação pelo menu (usa "Favoritos" e "Solicitações - Grupo")
async def navegar_menu(page):
    # print("Navegando no menu...")
    # await page.wait_for_selector('div[role="button"]:has-text("Favoritos")', timeout=15000)
    # await page.click('div[role="button"]:has-text("Favoritos")')
    # await page.wait_for_selector('span:has-text("Solicitações - Grupo")', timeout=15000)
    # await page.click('span:has-text("Solicitações - Grupo")')
    # await page.wait_for_timeout(3000)
    # print("Menu navegado.")
    print("- Navegando no menu...")
    await page.wait_for_selector('div[role="button"]:has-text("Todos")', timeout=15000)
    await page.click('div[role="button"]:has-text("Todos")')
    await page.wait_for_timeout(1000)
    
    # digitar "Solicitações do(s)"
    await page.keyboard.type("Solicitações do(s)")
    
    await page.wait_for_selector('span:has-text("Solicitações do(s)")', timeout=15000)
    await page.click('span:has-text("Solicitações do(s)")')
    # await page.wait_for_timeout(300000)
    print("- Menu navegado.")

# Função para preencher o campo item via OpenCV (usa o template "input_filtro_item_grupo.png")
async def preencher_item(page, item):
    
    # print("Preenchendo campo item via OpenCV...")
    # screenshot_path = "screenshot.png"
    # await page.screenshot(path=screenshot_path, full_page=True)
    # print("Screenshot capturada.")

    # img = cv2.imread(screenshot_path)
    # template = cv2.imread("input_filtro_item_grupo.png")
    
        
    print("- Preenchendo campo item via OpenCV...")
    screenshot_path = os.path.join(TEMPLATES_DIR, "screenshot.png")
    await page.screenshot(path=screenshot_path, full_page=True)
    # print(f"Screenshot capturada e salva em: {screenshot_path}")

    img = cv2.imread(screenshot_path)
    template = cv2.imread(os.path.join(TEMPLATES_DIR, "input_filtro_item_grupo.png"))
    
    
    
    if img is None:
        raise Exception("- [Erro] Ao carregar a screenshot.")
    if template is None:
        raise Exception("- [Erro] Ao carregar o template 'input_filtro_item_grupo.png'. Verifique se o arquivo existe no caminho correto.")

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8  # Ajuste esse valor se necessário
    loc = np.where(res >= threshold)
    points = list(zip(*loc[::-1]))
    
    if not points:
        raise Exception("- [Erro] Template não encontrado na screenshot.")
    
    x, y = points[0]
    h, w = template_gray.shape
    center_x = x + w / 2
    center_y = y + h / 2
    print(f"- Elemento item encontrado em: x={center_x:.0f}, y={center_y:.0f}")
    
    await page.mouse.move(center_x, center_y)
    await page.mouse.click(center_x, center_y)
    print("- Clique realizado no elemento item via OpenCV.")
    
    await page.wait_for_timeout(1000)
    await page.keyboard.type(item, delay=50)
    await page.wait_for_timeout(1000)
    await page.keyboard.press("Enter")
    print("- Valor preenchido e Enter pressionado no campo item.")

# Função genérica para esperar que um texto fique visível via OCR e clicar nele
async def click_text(page, texto, timeout=15, interval=1):
    """
    Aguarda até que um elemento cujo texto inicie com 'texto' seja encontrado via OCR e clica nele.
    :param page: objeto page do Playwright.
    :param texto: string que deve iniciar o texto do elemento.
    :param timeout: tempo máximo de espera em segundos.
    :param interval: intervalo de verificação em segundos.
    """
    print(f"- Aguardando que o texto que inicia com '{texto}' fique visível...")
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
                print(f"- Texto encontrado: '{t}' em {target_box}")
                break
        
        if target_box:
            x, y, w, h = target_box
            center_x = x + w / 2
            center_y = y + h / 2
            print(f"- Elemento localizado em: x={center_x:.0f}, y={center_y:.0f}")
            await page.mouse.move(center_x, center_y)
            await page.mouse.click(center_x, center_y)
            print(f"- Clique realizado no elemento que inicia com '{texto}' via OCR.")
            return
        
        if time.time() - start_time > timeout:
            raise Exception(f"- [Erro] Timeout: o texto que inicia com '{texto}' não ficou visível em {timeout} segundos.")
        
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
        
#         screenshot_path = os.path.join(TEMPLATES_DIR, "screenshot.png")
#         await page.screenshot(path=screenshot_path, full_page=True)
#         print(f"Screenshot capturada e salva em: {screenshot_path}")

#         # Carrega a screenshot e o template com OpenCV
#         img = cv2.imread(screenshot_path)
#         template = cv2.imread(os.path.join(TEMPLATES_DIR, template_filename))
        
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
    print(f"- Localizando elemento usando o template '{template_filename}'...")
    import time
    start_time = time.time()
    
    while True:
        # screenshot_path = "screenshot.png"
        # await page.screenshot(path=screenshot_path, full_page=True)
        # print("Screenshot capturada.")
    
        # # Carrega a screenshot e o template com OpenCV
        # img = cv2.imread(screenshot_path)
        # template = cv2.imread(template_filename)
        
        screenshot_path = os.path.join(TEMPLATES_DIR, "screenshot.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"- Screenshot capturada e salva em: {screenshot_path}")

        # Carrega a screenshot e o template com OpenCV
        img = cv2.imread(screenshot_path)
        template = cv2.imread(os.path.join(TEMPLATES_DIR, template_filename))
        if img is None:
            raise Exception("- [Erro] Ao carregar a screenshot.")
        if template is None:
            raise Exception(f"- [Erro] Ao carregar o template '{template_filename}'. Verifique se o arquivo existe.")
    
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
            print(f"- Elemento encontrado com o template '{template_filename}' em: x={center_x:.0f}, y={center_y:.0f}")
            
            # Posiciona o mouse no elemento encontrado
            await page.mouse.move(center_x, center_y)
            # Aguarda o delay definido antes de clicar
            await asyncio.sleep(delay)
            
            if texto:
                # Se um texto for fornecido, digita o texto
                await page.keyboard.type(texto, delay=10)
                print(f"- Texto '{texto}' digitado.")
                await page.keyboard.press("Enter")
                
                return  # Encerra a função após o clique
            
            if enter:
                # Se enter for True, simula o pressionamento da tecla Enter após o clique
                await page.keyboard.press("Enter")
                print(f"- Tecla Enter realizado no elemento utilizando o template '{template_filename}'.")
            elif not enter:
                # Realiza o clique
                await page.mouse.click(center_x, center_y)
                print(f"- Clique realizado no elemento utilizando o template '{template_filename}'.")
                
            
            

            return  # Encerra a função após o clique
    
        if time.time() - start_time > timeout:
            raise Exception(f"- [Erro] Timeout: Template '{template_filename}' não encontrado na screenshot após {timeout} segundos.")
    
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
    

async def atualizar_registro(dado, **kwargs):
    """
    Atualiza as colunas do registro conforme os parâmetros passados em kwargs
    
    Args:
        dado: Objeto do modelo TblProcessos
        **kwargs: Pares de chave-valor com as colunas e valores a serem atualizados
        Exemplo:
        await atualizar_registro(dado, atribuido=True)  # Atualiza só atribuido
        await atualizar_registro(dado, classificado=True, ja_classificado=True)  # Atualiza duas colunas
        await atualizar_registro(dado, atribuido=True, classificado=True, ja_atribuido=True)  # Atualiza várias colunas
    """
    try:
        # Atualiza o objeto com todos os valores passados em kwargs
        TblProcessos.atualizar_status_processo(dado, **kwargs)
        print(f"- ID: {dado.id} Atualizado com sucesso")
    except Exception as e:
        print(f"- ID: {dado.id} - item: {dado.item} - Erro ao atualizar o banco de dados")
        print(f"- Erro ao atualizar o processo: {e}")

# Função principal
async def run():
    async with async_playwright() as p:
        
        # Obtém usuários com processos pendentes
        usuarios = TblProcessos.listar_usuarios_com_processos_pendentes()
        
        if not usuarios:
            print("- Não há usuários com processos pendentes")
            return
            
        print(f"- Encontrados {len(usuarios)} usuários com processos pendentes")
        
        # aqui eu preciso de um loop para cada usuario
        for usuario in usuarios:
            print("-" * 65, flush=True)
            print(f"- Atribuindo item(s) para o usuario: {usuario}")
            
            # Obtém processos não atribuídos
            processos = TblProcessos.processos_nao_atribuidos_por_usuario(usuario, valor=True)
            
            if not processos:
                print(f"- Nenhum processo pendente de atribuição encontrado para o usuário {usuario}.")
                continue  # Continua para o próximo usuário em vez de retornar
            
            print(f"- Iniciando atribuição para {len(processos)} processos do usuário {usuario}")
            
        
        
        

        
            # Inicia o navegador em modo anônimo (incognito) e sem viewport para usar o tamanho real da janela
            browser = await p.chromium.launch(headless=False, args=["--incognito"])
            context = await browser.new_context(viewport=None)
            page = await context.new_page()
            
            await login(page, usuario)
            
            for dado in processos:
                
                print("*" * 50)                
                
                await navegar_menu(page)
                
                # ----------------------------------------------------------------
                # ATRIBUIR item
                # ----------------------------------------------------------------
                print("-" * 50) 
                print("- Atribuir item:")
                print("-" * 50) 
                try:
                    print(dado.id, dado.item)                
                    # Preenche o campo item com o valor "2201043253"
                    await preencher_item(page, dado.item)
                    
                    sleep(2)
                
                    # Usa a função genérica para clicar em um elemento cujo texto inicia com "SAJ" via OCR
                    await click_text(page, "SAJ", timeout=15, interval=1)
                    
                    # Clicar em ATRIBUIR PARA MIM
                    try:
                        await clicar_por_template(page, "btn_atribuir_para_mim.png", threshold=0.8)
                        print(f"- ID: {dado.id} - item: {dado.item} Atribuido com sucesso")
                    except Exception as e:
                        await atualizar_registro(dado, ja_atribuido=True)  # Atualiza só atribuido
                        
                    
                    # Salva ATRIBUIÇÃO item
                    try:
                        TblProcessos.atualizar_status_processo(dado, atribuido=True)
                        print(f"- ID: {dado.id} ATRIBUIÇÃO Atualizada com sucesso")
                    except Exception as e:
                        print(f"- ID: {dado.id} - item: {dado.item} Atribuido, MAS DEU ERRO AO ATUALIZOU O BANCO DE DADOS")
                        print(f"- Erro ao atualizar o processo: {e}")
                    
                except Exception as e:
                    await atualizar_registro(dado, ja_atribuido=True)  # Atualiza só atribuido
                    continue
                
                    
                await page.wait_for_timeout(3000)
                
                
                # ----------------------------------------------------------------
                # CLASSIFICAR PRÉ-SENTENÇA
                # ----------------------------------------------------------------
                print("-" * 50) 
                print("- Classificar Pré-Sentença:")
                print("-" * 50)
                try:
                    #clicar no select tipo sentença
                    await clicar_por_template(page, "select_tipo_sentenca.png", threshold=0.8, timeout=15, interval=1)
                    print('- CLICOU NO SELECT TIPO SENTENÇA')
                    sleep(1)
                    if 'pré' in dado.tipo_sentenca.lower(): #if dado['fase'] == "Pré-sentença":  #
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
                    print('- SOLICITAR APROVAÇÃO BANCO')
                    await clicar_por_template(page, "option_solicitar_aprovacao_banco.png", threshold=0.8, timeout=15, interval=1, delay=1, texto="solicitar")
                    
                    # print('CONTRA PROPOSTA')
                    # clica no input Valor Contra proposta
                    await clicar_por_template(page, "input_contra_proposta.png", threshold=0.8, timeout=15, interval=1)
                    
                    # print("DIGITANDO O VALOR DA CONTRA PROPOSTA:",str(dado.contra).replace('.', ','))
                    print("- DIGITANDO O VALOR DA CONTRA PROPOSTA:",f"{float(dado.contra):.2f}".replace('.', ','))
                    
                    # Preencher o valor da contra proposta
                    # await digitar_valores(page, str(dado.contra).replace('.', ','), delay=50)
                    await digitar_valores(page, f"{float(dado.contra):.2f}".replace('.', ','), delay=50)

                    # sleep(300)
                    # Clicar no botão Atualizar
                    await clicar_por_template(page, "btn_atualizar_valor.png", threshold=0.8, timeout=15, interval=1, delay=1)
                
                except Exception as e:
                    print(f"- [Erro] Ao classificar o item: {dado.item}")
                    continue
                
                try:
                    # Salva o PRÉ-SENTENÇA
                    # TblProcessos.atualizar_status_processo(dado, classificado=True)
                    await atualizar_registro(dado, classificado=True)  # Atualiza só atribuido
                    print(f"- ID: {dado.id} CLASSIFICAÇÃO Atualizada com sucesso")
                except Exception as e:
                    print(f"- ID: {dado.id} - item: {dado.item} Classificou, MAS DEU ERRO AO CLASSIFICOU O BANCO DE DADOS")
                    print(f"- [Erro] Ao atualizar o processo: {e}")
                    
                await page.wait_for_timeout(3000)
                

            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
