# Project

The deepRAG project seeks to extend classic retrieval using vector databases to optional utilize other search technologies for extended results.
This will initially be done by utilizing graph databases to help answer queries related to content summaries that aren't directly related to snippets of content.

The architecture of this project is located in [ARCHITECTURE.MD](./docs/ARCHITECTURE.md).

## Running the project

Run the following command.
```poetry install```

Then, select the interpreter in the poetry cache.

### API authentication and sessions

The API and frontend require two additional settings in `.env`:

| Variable | Description |
| --- | --- |
| `API_KEY` | Shared secret (min. 16 chars) the frontend sends in the `X-API-Key` header. All API routes (`/session`, `/deepRAG`, `/vectorRAG`) require it. |
| `SESSION_SECRET` | Server-only secret (min. 32 chars) used to HMAC-sign session tokens. |

Generate them with e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"` and keep them out of source control.

Clients must obtain a session token from `POST /session` and pass it as `session_id` to `/deepRAG/invoke`. The API rejects tokens it did not sign, and conversation history is stored in Redis as JSON under a server-derived key (`deeprag:history:<id>`).

> **Note:** the shared API key authenticates the frontend, not individual end users. Do not expose the API directly to untrusted clients; if you need per-user isolation beyond the frontend, add end-user authentication (e.g. Microsoft Entra ID) and bind sessions to the user identity.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
