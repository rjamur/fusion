from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from .services import get_ai_response
from .models import Message

class GetAIResponseTests(TestCase):

    @patch('chatbot.services.genai')
    def test_get_ai_response_success(self, mock_genai):
        """
        Testa se get_ai_response formata o histórico e retorna o texto da IA com sucesso.
        """
        # 1. Arrange: Configura o mock para simular a API do Gemini
        mock_response = MagicMock()
        mock_response.text = "Esta é uma resposta mockada da IA."
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.return_value = mock_response
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat_session
        mock_genai.GenerativeModel.return_value = mock_model

        # Cria um histórico de conversa falso
        conversation_history = [
            MockMessage(sender='user', text='Olá!'),
            MockMessage(sender='user', text='Qual o seu nome?'),
        ]

        # 2. Act: Executa a função que está sendo testada
        response_text = get_ai_response(conversation_history)

        # 3. Assert: Verifica se o resultado é o esperado
        self.assertEqual(response_text, "Esta é uma resposta mockada da IA.")
        mock_genai.configure.assert_called_once_with(api_key="fake-api-key-for-testing")
        mock_model.start_chat.assert_called_once()
        mock_chat_session.send_message.assert_called_once()

    @patch('chatbot.services.genai')
    def test_get_ai_response_api_error(self, mock_genai):
        """
        Testa o comportamento de get_ai_response quando a API do Gemini lança uma exceção.
        """
        # 1. Arrange: Configura o mock para levantar uma exceção
        mock_genai.GenerativeModel.side_effect = Exception("Erro de conexão simulado")

        conversation_history = [MockMessage(sender='user', text='Isso vai dar erro?')]

        # 2. Act: Executa a função
        response_text = get_ai_response(conversation_history)

        # 3. Assert: Verifica se a mensagem de erro amigável foi retornada
        expected_error_message = "Desculpe, estou com problemas para me conectar com minha inteligência. Tente novamente mais tarde."
        self.assertEqual(response_text, expected_error_message)
