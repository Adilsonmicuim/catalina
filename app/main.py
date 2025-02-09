import os
import asyncio
import subprocess
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Caminho do log do Tomcat
LOG_PATH = "/opt/tomcat/logs/catalina.out"

# Servindo arquivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Servir a página inicial
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


# Função para transmitir logs
async def stream_logs(websocket: WebSocket):
    if not os.path.exists(LOG_PATH):
        await websocket.send_text("[ERRO] Arquivo de log não encontrado.")
        await websocket.close()
        return

    process = subprocess.Popen(["tail", "-f", LOG_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        while True:
            line = process.stdout.readline()
            if line:
                await websocket.send_text(line.strip())  # Envia o log
            await asyncio.sleep(0.1)  # Evita alto uso de CPU
    except Exception as e:
        await websocket.send_text(f"[ERRO] {str(e)}")
    finally:
        process.terminate()
        await websocket.close()


# Endpoint do WebSocket
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Conexão WebSocket estabelecida com sucesso!")
    await stream_logs(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
