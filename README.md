# Práticas Lambda + S3

Cole o arquivo inteiro da prática no `lambda_function.py` da sua Lambda e clique em Deploy.

Na prática 2, envie uma foto original JPG, PNG ou WEBP de até 5 MB para `uploads/` no seu bucket. A figurinha será criada em `stickers/`, no mesmo bucket. O gatilho S3 deve filtrar apenas `uploads/`.

Esta versão inclui o novo acabamento das figurinhas. Para atualizar uma figurinha antiga, envie novamente sua foto após publicar o código.

Para participar do álbum da turma, use o link fornecido pelo professor e selecione a foto original, não o SVG.

A raridade depende do hash da foto: 25% lendaria, 25% rara, 50% comum para fotos novas.
O mesmo arquivo sempre recebe a mesma raridade. Figurinhas ja criadas sao preservadas ao reenviar a foto.
