# ReplayX
Sistema de replay instantaneo com galeria privada e marca do contratante.

## Fluxo do produto

- A pagina inicial apresenta o servico e permite contratar uma conta master.
- O master configura marca d'agua/logo e cria usuarios de acesso aos replays.
- Cada empresa recebe um token proprio para o botao ESP32.
- Usuarios comuns acessam somente os videos vinculados a sua empresa.
- Novos videos podem receber a propaganda configurada antes do upload.

## Configuracao local

Crie o arquivo `.env` a partir de `.env.example` e preencha localmente:

```text
CLOUD_NAME=
API_KEY=
API_SECRET=
SECRET_KEY=
OBS_HOST=localhost
OBS_PORT=4455
OBS_PASSWORD=
```

O arquivo `.env` contem credenciais e nao deve ser enviado ao Git.
O token de replay agora e criado no painel master e deve ser copiado para o
`secrets.h` do ESP32 correspondente ao contratante.

## Pasta de replays do OBS

Configure o caminho de gravacao/replay buffer do OBS para:

```text
D:\Prototipo Camera replay\Python\Projeto\core\uploads
```

O dashboard e o monitor de uploads procuram os arquivos nessa pasta. Eles
aceitam a saida `.mkv` do OBS. Quando um replay novo e salvo, o monitor executa
um remux automatico para `.mp4`, sem recodificar o video, remove o `.mkv`
original apos sucesso e disponibiliza o `.mp4` no dashboard.

## FFmpeg

O remux requer o executavel FFmpeg. Use uma das opcoes:

```text
D:\Prototipo Camera replay\Ffmpeg\bin\ffmpeg.exe
```

ou configure no arquivo `.env`:

```text
FFMPEG_PATH=C:\caminho\para\ffmpeg.exe
```

O OBS pode continuar salvando os replays em formato `.mkv`, que e mais seguro
caso a gravacao seja interrompida antes de finalizar.

## ESP32

Na pasta `Arduino\Projeto ESP32\ReplayWiFi`, crie `secrets.h` a partir de
`secrets.example.h` e informe a rede Wi-Fi e sua senha. O arquivo `secrets.h`
tambem deve permanecer somente na maquina local. O botao envia `POST /replay`
com o cabecalho `X-Replay-Token`, que precisa corresponder ao `REPLAY_TOKEN` do
servidor.

## Execucao

Instale as dependencias:

```text
pip install -r requirements.txt
```

Com o OBS e seu Replay Buffer ativos, execute em terminais separados:

```text
python app.py
python replay_watcher.py
```

O watcher processa arquivos pendentes ao iniciar, converte MKV para MP4,
associa a captura ao contratante que pressionou o botao, aplica sua marca
quando configurada, envia o resultado ao Cloudinary e grava a URL no banco
local. O dashboard autenticado lista apenas os uploads da mesma empresa e as
rotas de reproducao/download verificam o usuario antes de entregar o video.
Falhas temporarias de processamento sao tentadas novamente pelo watcher.
