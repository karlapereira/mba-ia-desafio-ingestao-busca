from unittest.mock import MagicMock, patch

import chat


def _run(inputs, chain):
    with patch.object(chat, "search_prompt", return_value=chain), \
            patch("builtins.input", side_effect=inputs):
        chat.main()


def test_inicializacao_falha_exibe_mensagem(capsys):
    _run([], None)
    assert "Não foi possível iniciar o chat" in capsys.readouterr().out


def test_responde_pergunta_e_encerra_com_sair(capsys):
    chain = MagicMock(return_value="10 milhões")
    _run(["Qual o faturamento?", "sair"], chain)
    chain.assert_called_once_with("Qual o faturamento?")
    assert "RESPOSTA: 10 milhões" in capsys.readouterr().out


def test_ignora_entrada_vazia(capsys):
    chain = MagicMock(return_value="x")
    _run(["", "   ", "sair"], chain)
    chain.assert_not_called()


def test_erro_em_uma_pergunta_nao_encerra_o_chat(capsys):
    chain = MagicMock(side_effect=[RuntimeError("API fora"), "ok"])
    _run(["p1", "p2", "sair"], chain)
    out = capsys.readouterr().out
    assert "Erro ao processar a pergunta: API fora" in out
    assert "RESPOSTA: ok" in out


def test_ctrl_c_ou_eof_encerra_sem_erro():
    _run(KeyboardInterrupt(), MagicMock())
    _run(EOFError(), MagicMock())
