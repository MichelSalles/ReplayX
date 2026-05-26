from obsws_python import ReqClient

client = ReqClient(
    host='localhost',
    port=4455,
    password=''
)

def salvar_replay():

    client.save_replay_buffer()

    print("REPLAY SALVO!")