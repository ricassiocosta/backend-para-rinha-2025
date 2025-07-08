# Backend Para Rinha 2025

Este repositório contém a implementação de um backend para o desafio "Rinha de Backend 2025". O projeto foi desenvolvido em Python, utilizando práticas modernas de desenvolvimento assíncrono e integração com gateways de pagamento.

## Descrição

O sistema é responsável por processar pagamentos de forma resiliente, utilizando múltiplos gateways e realizando fallback automático em caso de falha. Ele também expõe endpoints para monitoramento de saúde e integrações externas.

## Arquitetura do Projeto

```
+---------+        +-------+         +--------+
|  API    |<-----> | Queue | <-----> | Worker |
+---------+        +-------+         +--------+
                                      ^   |
                                      |   v
                                    +--------+
                                    |Health  |
                                    +--------+
                                      ^   |
                                      |   v
                                    +-------+
                                    | Cache |
                                    +-------+
                                        |
                                        v
                 +-------------------+     +-------------------+
                 | Payment Processor |     | Payment Processor |
                 |        1          |     |        2          |
                 +-------------------+     +-------------------+
```

- **Cliente**: Usuário ou sistema externo que faz requisições de pagamento.
- **API (FastAPI)**: Recebe as requisições e orquestra o fluxo.
- **Processor**: Processa e envia pedidos para a fila.
- **Fila (Redis)**: Armazena pedidos de pagamento de forma assíncrona.
- **Worker**: Consome a fila e executa o processamento dos pagamentos.
- **Health**: Verifica a saúde dos gateways.
- **Storage**: Persistência dos dados.
- **Gateways**: Serviços externos de pagamento (Default e Fallback).

## Estrutura do Projeto

```
├── app/
│   ├── __init__.py
│   ├── config.py         # Configurações do sistema
│   ├── health.py         # Lógica de healthcheck dos gateways
│   ├── main.py           # Ponto de entrada da aplicação
│   ├── models.py         # Modelos de dados
│   ├── processor.py      # Processamento e envio de pagamentos
│   ├── queue.py          # Gerenciamento de filas
│   ├── storage.py        # Persistência de dados
│   └── worker.py         # Worker assíncrono para processamento
├── migrations/
│   └── 001_init.sql      # Script de criação do banco de dados
├── requirements.txt      # Dependências do projeto
├── Dockerfile            # Dockerização da aplicação
├── docker-compose.yml    # Orquestração de containers
└── LICENSE
```

## Como rodar o projeto

1. **Clone o repositório:**

   ```bash
   git clone <url-do-repositorio>
   cd backend-para-rinha-2025
   ```

2. **Configure as variáveis de ambiente:**

   - Edite o arquivo `.env` (se necessário) ou ajuste as variáveis diretamente no `docker-compose.yml`.

3. **Suba os containers:**

   ```bash
   docker-compose up --build
   ```

4. **Acesse a aplicação:**
   - Os endpoints estarão disponíveis conforme configurado no `docker-compose.yml`.

## Principais Funcionalidades

- Processamento resiliente de pagamentos
- Fallback automático entre gateways
- Healthcheck dos serviços integrados
- Estrutura modular e fácil de manter

## Tecnologias Utilizadas

- Python 3.12+
- httpx (requisições assíncronas)
- Docker & Docker Compose

## Scripts Úteis

- `docker-compose up --build` — Sobe a aplicação e dependências
- `docker-compose down` — Para e remove os containers

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

Desenvolvido para o desafio Rinha de Backend 2025 🚀
