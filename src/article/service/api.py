import aiohttp

from loguru import logger


class RequestArticleApi:
    def __init__(self, api_key):
        self.api_key: str = api_key
    
    async def request_article(
        self,
        client: aiohttp.ClientSession,
        category: str,
        published_at: str,
    ) -> list:
        try:
            url = (
                "https://newsapi.org/v2/everything"
                f"?q={category}"
                "&searchIn=title"
                "&language=en"
                f"&from={published_at}"
                f"&to={published_at}"
                f"&apiKey={self.api_key}"
            )
            async with client.get(url) as response:
                data: dict = await response.json()
                assert isinstance(data, dict)
                logger.debug("Данные от API полученны")
                if data.get("status", None) != "ok":
                    raise aiohttp.client.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Статус ответа {response.status}",
                    )
                logger.debug("Запрос успешен. Никаких проблем не возникло")
                return data["articles"]
        except aiohttp.client.ClientResponseError as error:
            logger.error(f"Статус API запроса {error.status}")
            return {
                "status": error.status,
                "url": error.request_info.url,
                "message": error.message,
            }
        except aiohttp.client.ClientError as error:
            logger.error(
                f"Ошибка при запросе. \nURL: {url}. \nDate: {published_at}. \nCategory: {category}. \nDescription: {str(error)}"
            )
            return {
                "status": "error",
                "message": "Возникла ошибка при попытке получить данные",
                "url": url,
                "description": str(error),
            }
