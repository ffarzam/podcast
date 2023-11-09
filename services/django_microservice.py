import httpx

from config.config import get_settings

settings = get_settings()


class Django:
    channel_list_url = settings.CHANNEL_LIST_URL
    items_list_url = settings.ITEMS_LIST_URL
    get_channel_url = settings.GET_CHANNEL_URL
    get_item_url = settings.GET_ITEM_URL

    async def channel_list(self, request, page):
        header = {"unique_id": request.state.unique_id}
        params = {}
        if page:
            params.update({"page": page})
        async with httpx.AsyncClient(headers=header) as client:
            response = await client.get(self.channel_list_url, params=params)

        # response.raise_for_status()
        return response

    async def items_list(self, channel_id, request, page):
        header = {"unique_id": request.state.unique_id}
        params = {}
        if page:
            params.update({"page": page})
        async with httpx.AsyncClient(headers=header) as client:
            response = await client.get(f"{self.items_list_url}{channel_id}/", params=params)
        # response.raise_for_status()
        return response

    async def get_channel(self, channel_id, request):
        header = {"unique_id": request.state.unique_id}
        async with httpx.AsyncClient(headers=header) as client:
            response = await client.get(f"{self.get_channel_url}{channel_id}/")
        # response.raise_for_status()
        return response

    async def get_item(self, channel_id, item_id, request):
        header = {"unique_id": request.state.unique_id}
        async with httpx.AsyncClient(headers=header) as client:
            response = await client.get(f"{self.get_item_url}{channel_id}/{item_id}/")
        # response.raise_for_status()
        return response


django_client = Django()


def get_django_client():
    return django_client
