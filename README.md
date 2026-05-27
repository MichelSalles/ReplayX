# ReplayX
Um sistema de Camera Replay "Diferenciado"

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
tambem deve permanecer somente na maquina local.
