import os
import asyncio
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional

app = FastAPI()

# Caminho do log do Tomcat
LOG_PATH = "/opt/tomcat/logs/catalina.out"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Servindo arquivos estáticos
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


async def run_tail_process(log_path: str) -> Optional[asyncio.subprocess.Process]:
    """
    Inicia um subprocesso 'tail -F <log_path>' e retorna um objeto asyncio.subprocess.Process.
    Em caso de falha (log inexistente ou comando 'tail' indisponível), retorna None.
    """
    if not os.path.exists(log_path):
        print(f"[ERRO] Arquivo de log '{log_path}' não encontrado.")
        return None

    try:
        process = await asyncio.create_subprocess_exec(
            "tail", "-n", "10", "-F", log_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        return process
    except FileNotFoundError:
        # O comando 'tail' pode não existir em sistemas minimalistas
        print("🔴 Comando 'tail' não encontrado no sistema.")
    except Exception as e:
        print(f"🔴 Falha ao iniciar o subprocesso 'tail': {e}")
    return None


async def stream_logs(websocket: WebSocket, process: asyncio.subprocess.Process):
    """
    Lê as linhas de 'tail -F' e envia para o cliente WebSocket.
    Também envia "ping" para manter a conexão viva.
    """
    print("🟢 WebSocket conectado:", websocket.client)

    # Precisamos ler stdout e stderr de forma assíncrona
    # para não bloquear o loop principal.
    async def read_stdout():
        while True:
            if process.stdout.at_eof():
                break
            line = await process.stdout.readline()
            if not line:
                await asyncio.sleep(0)
                continue
            # Envia a linha para o cliente
            await websocket.send_text(line.decode().rstrip())
            # Envia ping para manter a conexão viva
            await websocket.send_text("ping")
            await asyncio.sleep(0)

    async def read_stderr():
        while True:
            if process.stderr.at_eof():
                break
            line = await process.stderr.readline()
            if line:
                # Se quiser, envie o stderr como texto de log
                # ou apenas imprima no servidor.
                print("Stderr:", line.decode().rstrip())
            await asyncio.sleep(0)

    # Criamos tarefas separadas para stdout e stderr
    stdout_task = asyncio.create_task(read_stdout())
    stderr_task = asyncio.create_task(read_stderr())

    # Ficamos aguardando até que o cliente desconecte
    # ou o subprocesso finalize
    try:
        await websocket.accept()
        # Aguarda até que alguma destas coroutines termine
        done, pending = await asyncio.wait(
            [stdout_task, stderr_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Caso alguma tenha terminado, cancelamos a outra
        for task in pending:
            task.cancel()

    except WebSocketDisconnect:
        print("🔴 Cliente desconectado.")
    except Exception as e:
        print(f"🔴 Erro WebSocket: {e}")
    finally:
        # Garantimos que paramos o subprocess e fechamos a conexão
        print("🔌 Encerrando subprocesso 'tail' e WebSocket.")
        process.terminate()
        await websocket.close()
        try:
            await process.wait()
        except ProcessLookupError:
            # Pode ser que o processo já tenha finalizado
            pass


@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    try:
        process = await run_tail_process(LOG_PATH)
        if not process:
            # Se não conseguir rodar o processo, avisa ao cliente
            await websocket.accept()
            await websocket.send_text(f"[ERRO] Não foi possível iniciar leitura do log '{LOG_PATH}'")
            await websocket.close()
            return

        # Se der certo, inicia transmissão
        await stream_logs(websocket, process)

    except Exception as e:
        print(f"🔴 Erro ao aceitar WebSocket: {e}")
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
