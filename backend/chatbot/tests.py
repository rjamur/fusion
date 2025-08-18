from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from .services import get_ai_response
from .models import Message

# Helper class to simulate the Message model without hitting the database
class MockMessage:
    def __init__(self, sender, text):
        self.sender = sender
        self.text = text

@override_settings(OPENAI_API_KEY="fake-api-key-for-testing")
class GetAIResponseTests(TestCase):

    @patch('chatbot.services.openai.ChatCompletion.create')
    def test_get_ai_response_success(self, mock_openai_create):
        """
        Testa se get_ai_response formata o histórico e retorna o texto da IA com sucesso.
        """
        # 1. Arrange: Configura o mock para simular a API da OpenAI
        mock_choice = MagicMock()
        mock_choice.message = {'content': 'Esta é uma resposta mockada da IA.'}

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai_create.return_value = mock_response


        # Cria um histórico de conversa falso
        conversation_history = [
            MockMessage(sender='user', text='Olá!'),
            MockMessage(sender='user', text='Qual o seu nome?'),
        ]

        # 2. Act: Executa a função que está sendo testada
        response_text = get_ai_response(conversation_history)

        # 3. Assert: Verifica se o resultado é o esperado
        self.assertEqual(response_text, "Esta é uma resposta mockada da IA.")
        mock_openai_create.assert_called_once()

    @patch('chatbot.services.openai.ChatCompletion.create')
    def test_get_ai_response_api_error(self, mock_openai_create):
        """
        Testa o comportamento de get_ai_response quando a API da OpenAI lança uma exceção.
        """
        # 1. Arrange: Configura o mock para levantar uma exceção
        mock_openai_create.side_effect = Exception("Erro de conexão simulado")

        conversation_history = [MockMessage(sender='user', text='Isso vai dar erro?')]

        # 2. Act: Executa a função
        response_text = get_ai_response(conversation_history)

        # 3. Assert: Verifica se a mensagem de erro amigável foi retornada
        expected_error_message = "Desculpe, estou com problemas para me conectar com minha inteligência. Tente novamente mais tarde."
        self.assertEqual(response_text, expected_error_message)
