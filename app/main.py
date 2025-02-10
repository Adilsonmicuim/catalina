import os
import asyncio
import subprocess
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Form,
    Response,
    status
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

# -------- CONFIG BASICA -------- #
USER_VALIDO = "tomcat"
SENHA_VALIDA = "tomcat"

LOG_PATH = "/opt/tomcat/logs/catalina.out"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -------- ROTA DE LOGIN -------- #
@app.get("/login")
def serve_login_page():
    """
    Exibe a página de login (login.html).
    """
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.post("/do_login")
def do_login(username: str = Form(...), password: str = Form(...)):
    """
    Processa o formulário de login.
    """
    if username == USER_VALIDO and password == SENHA_VALIDA:
        # Se login OK, criar uma resposta com cookie "session=ok"
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        # Define um cookie "session". Use algo mais seguro em produção (JWT, etc.)
        response.set_cookie(
            key="session",
            value="ok",
            httponly=True,
            max_age=3600 # expira em 1 hora
            # max_age=36000  # expira em 10 horas
        )
        return response
    else:
        # Se credenciais inválidas, redireciona para /login novamente
        resp = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        return resp


# -------- VERIFICA SESSÃO -------- #
def is_authenticated(request: Request) -> bool:
    """
    Checa se o cookie 'session' existe e é 'ok'.
    Em produção você faria algo mais robusto (tokens, JWT, etc.).
    """
    session_value = request.cookies.get("session")
    return (session_value == "ok")


# -------- ROTA PRINCIPAL / PROTEGIDA -------- #
@app.get("/")
def serve_index(request: Request):
    """
    Se não estiver logado, redireciona para /login.
    Senão, serve o index.html (que carrega script.js e mostra logs).
    """
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# -------- WEBSOCKET PROTEGIDO -------- #
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket, request: Request = None):
    """
    Precisamos verificar se o usuário está autenticado ANTES de aceitar o WebSocket.
    Entretanto, com WebSockets, não há cabeçalho Cookie tão simples.
    Mas FastAPI repassa cookies em websocket.headers. Podemos checar manualmente.
    """
    # Vamos checar o cookie no handshake
    session_cookie = websocket.headers.get("cookie", "")
    # "cookie" é uma string tipo "session=ok; outroscookies=..."
    if "session=ok" not in session_cookie:
        # Fecha a conexão imediatamente, usuário não autenticado
        await websocket.close()
        return

    # Se passou, podemos servir os logs
    await stream_logs(websocket)


# -------- FUNÇÃO stream_logs (igual à sua anterior) -------- #
async def stream_logs(websocket: WebSocket):
    try:
        await websocket.accept()
        print("🟢 WebSocket conectado:", websocket.client)

        if not os.path.exists(LOG_PATH):
            await websocket.send_text("[ERRO] Arquivo de log não encontrado.")
            await websocket.close()
            return

        # Inicia o `tail -F` sem buffering
        process = subprocess.Popen(
            ["tail", "-n", "10", "-F", LOG_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Evita buffering do Python
            universal_newlines=True
        )

        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    await asyncio.sleep(0.0)
                    continue

                if websocket.client_state.name == "CONNECTED":
                    # Envia linha de log
                    await websocket.send_text(line.strip())
                    # Envia ping
                    await websocket.send_text("ping")
                else:
                    print("🔌 Cliente desconectado.")
                    break

                await asyncio.sleep(0)
        except WebSocketDisconnect:
            print("🔴 Cliente desconectado.")
        except Exception as e:
            print(f"🔴 Erro WebSocket: {e}")
        finally:
            process.terminate()
            await websocket.close()
            print("🔌 Conexão WebSocket encerrada.")

    except Exception as e:
        print(f"🔴 Erro ao aceitar WebSocket: {e}")


# -------- INICIAR SERVIDOR -------- #
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
