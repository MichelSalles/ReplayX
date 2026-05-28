# ReplayX

Sistema de replay esportivo instantâneo com galeria privada, upload automático em nuvem e branding personalizado por contratante.

---

# Visão Geral

O ReplayX permite que arenas esportivas, quadras e organizadores de eventos ofereçam replays instantâneos através de um botão físico ESP32 integrado ao OBS Studio.

Quando o botão é pressionado:

1. O OBS salva o Replay Buffer
2. O sistema detecta automaticamente o novo replay
3. O vídeo pode receber branding personalizado
4. O replay é enviado automaticamente para a nuvem
5. O vídeo aparece no dashboard privado da empresa

Cada contratante possui:

* Conta própria
* Branding personalizado
* Token exclusivo para ESP32
* Galeria privada
* Usuários isolados por empresa

---

# Arquitetura do Sistema

```text
ESP32
   ↓
Flask API
   ↓
OBS Replay Buffer
   ↓
Replay Watcher
   ↓
FFmpeg Processing
   ↓
Branding
   ↓
Cloudinary
   ↓
Dashboard
```

---

# Fluxo do Produto

* A página inicial apresenta o serviço e permite contratar uma conta master.
* O master configura marca d'água, logos e patrocinadores.
* Cada empresa recebe um token exclusivo para o botão ESP32.
* Usuários comuns acessam apenas os vídeos vinculados à própria empresa.
* Novos vídeos podem receber branding automaticamente antes do upload.

---

# Recursos

## Replay Instantâneo

Captura automática dos últimos segundos/minutos configurados no OBS.

## Multiempresa (SaaS)

Cada empresa possui:

* Usuários próprios
* Branding próprio
* Tokens próprios
* Replays isolados

## Branding Automático

Aplicação automática de:

* Logos
* Marcas d'água
* Patrocinadores

antes do upload final.

## Conversão Automática MKV → MP4

O sistema converte automaticamente os arquivos do OBS sem recodificação, preservando qualidade e velocidade.

## Dashboard Privado

Usuários visualizam apenas os vídeos autorizados da própria empresa.

## Retry Automático

Falhas temporárias de processamento são tentadas novamente automaticamente pelo watcher.

---

# Configuração Local

Crie o arquivo `.env` a partir de `.env.example`:

```env
CLOUD_NAME=
API_KEY=
API_SECRET=
SECRET_KEY=

OBS_HOST=localhost
OBS_PORT=4455
OBS_PASSWORD=

FFMPEG_PATH=C:\caminho\para\ffmpeg.exe
```

## Importante

* O arquivo `.env` contém credenciais privadas
* Nunca envie o `.env` para o GitHub
* Utilize `.gitignore`

O token de replay é criado no painel master e deve ser copiado para o `secrets.h` do ESP32 correspondente ao contratante.

---

# Pasta de Replays do OBS

Configure o caminho de gravação/replay buffer do OBS para:

```text
D:\Prototipo Camera replay\Python\Projeto\core\uploads
```

O dashboard e o monitor de uploads procuram os arquivos nessa pasta.

O sistema aceita a saída `.mkv` do OBS e executa automaticamente:

* Remux para `.mp4`
* Remoção do `.mkv` original após sucesso
* Disponibilização automática no dashboard

O OBS pode continuar salvando os replays em `.mkv`, formato mais seguro caso a gravação seja interrompida inesperadamente.

---

# FFmpeg

O ReplayX utiliza FFmpeg para:

* Remux MKV → MP4
* Aplicação de branding
* Futuras compressões e otimizações

Configure o executável:

```text
D:\Prototipo Camera replay\Ffmpeg\bin\ffmpeg.exe
```

ou no `.env`:

```env
FFMPEG_PATH=C:\caminho\para\ffmpeg.exe
```

---

# ESP32

Na pasta:

```text
Arduino\Projeto ESP32\ReplayWiFi
```

crie:

```text
secrets.h
```

a partir de:

```text
secrets.example.h
```

Configure:

* Rede Wi-Fi
* Senha
* Token do replay

O botão envia:

```http
POST /replay
```

com o cabeçalho:

```http
X-Replay-Token
```

O token deve corresponder ao token gerado pelo painel master.

---

# Execução

Instale as dependências:

```bash
pip install -r requirements.txt
```

Com OBS e Replay Buffer ativos, execute em terminais separados:

```bash
python app.py
```

```bash
python replay_watcher.py
```

---

# Processamento de Replay

O watcher:

* Processa arquivos pendentes ao iniciar
* Converte MKV para MP4
* Associa o replay ao contratante correto
* Aplica branding automaticamente
* Envia o resultado para Cloudinary
* Grava URLs no banco local

O dashboard autenticado:

* Lista apenas uploads da mesma empresa
* Protege rotas de reprodução e download
* Verifica permissões antes de entregar vídeos

---

# Estrutura do Projeto

```text
Projeto/
│
├── app.py
├── replay_watcher.py
├── requirements.txt
├── .env
│
├── core/
│   ├── uploads/
│   ├── branding/
│   ├── database/
│   ├── processing/
│   └── auth/
│
├── Arduino/
│   └── Projeto ESP32/
│
├── templates/
├── static/
└── instance/
```

---

# Roadmap

## MVP Atual

* Replay instantâneo
* Upload automático
* Dashboard web
* ESP32 trigger
* Cloudinary integration
* Branding automático
* Multiempresa
* Controle de acesso

## Próximas Funcionalidades

* Fila de processamento de replay
* Workers assíncronos
* Múltiplas câmeras
* Dashboard mobile
* QR Code para download rápido
* IA para highlights automáticos
* Analytics
* White-label completo
* Sistema de planos e pagamentos

---

# Arquitetura Futura

O ReplayX está evoluindo para uma arquitetura baseada em filas para suportar múltiplos acionamentos simultâneos sem conflitos.

Fluxo planejado:

```text
ESP32
   ↓
Queue
   ↓
Worker
   ↓
Processing Pipeline
   ↓
Upload
   ↓
Dashboard
```

Objetivos:

* Evitar conflitos simultâneos
* Melhorar estabilidade
* Aumentar escalabilidade
* Suportar múltiplas arenas simultaneamente

---

# Tecnologias Utilizadas

* Python
* Flask
* OBS WebSocket
* FFmpeg
* Cloudinary
* ESP32
* Watchdog
* SQLite
* HTML/CSS/JavaScript

---

# Segurança

O sistema implementa:

* Isolamento por empresa
* Autenticação
* Verificação de permissões
* Tokens exclusivos
* Proteção de credenciais via `.env`

---

# Licença

Projeto privado em desenvolvimento.
