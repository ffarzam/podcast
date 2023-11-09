from datetime import datetime
from uuid import uuid4

import pytz
from fastapi import APIRouter, Depends, status, Request, Response

from config.jwt_authentication import get_access_jwt_aut, AccessJWTBearer
from db.mongodb import get_podcast_database
from schemas.interactions import Comment
from services.django_microservice import get_django_client
from utils.user import find_user, check_channel_bookmark, check_episode_like, check_episode_bookmark

tz = pytz.timezone("Asia/Tehran")
django_client = get_django_client()
routers = APIRouter(prefix="/v1")


@routers.get("/channel_list/")
async def channel_list(request: Request, response: Response, page: str | None = None, db=Depends(get_podcast_database)):
    user_collection = db["users"]
    podcast_collection = db["podcast"]

    django_microservice_response = await django_client.channel_list(request, page)
    response.status_code = django_microservice_response.status_code
    data = django_microservice_response.json()

    user_id = await find_user(request)

    if response.status_code == 200:
        refined_data = []
        for channel in data["results"]:
            pre_data = {k: v for k, v in channel.items()}
            pre_data["is_bookmarked"], pre_data["bookmark_count"] = await check_channel_bookmark(user_id,
                                                                                                 pre_data["id"], db)
            refined_data.append(pre_data)

        data = refined_data

    return data


@routers.get("/items_list/{channel_id}/", status_code=status.HTTP_200_OK)
async def items_list(request: Request, response: Response, channel_id: int, page: str | None = None,
                     db=Depends(get_podcast_database)):
    django_microservice_response = await django_client.items_list(channel_id, request, page)
    response.status_code = django_microservice_response.status_code
    data = django_microservice_response.json()

    user_id = await find_user(request)

    if response.status_code == 200:
        refined_data = []
        for channel in data:
            pre_data = {k: v for k, v in channel.items() if k not in ["seconds_listened"]}
            pre_data["is_bookmarked"], pre_data["bookmark_count"] = await check_episode_bookmark(user_id, channel_id,
                                                                                                 pre_data["id"], db)
            pre_data["is_liked"], pre_data["liked_count"] = await check_episode_like(user_id, channel_id,
                                                                                     pre_data["id"], db)
            refined_data.append(pre_data)

        data = refined_data
    return data


@routers.get("/get_channel/{channel_id}/", status_code=status.HTTP_200_OK)
async def get_channel(request: Request, response: Response, channel_id: int, db=Depends(get_podcast_database)):
    django_microservice_response = await django_client.get_channel(channel_id, request)
    response.status_code = django_microservice_response.status_code
    data = django_microservice_response.json()
    user_id = await find_user(request)

    if response.status_code == 200:
        refined_data = {k: v for k, v in data.items()}
        refined_data["is_bookmarked"], refined_data["bookmark_count"] = await check_channel_bookmark(user_id,
                                                                                                     channel_id, db)
        data = refined_data
    return data


@routers.get("/get_item/{channel_id}/{item_id}/", status_code=status.HTTP_200_OK)
async def get_item(request: Request, response: Response, channel_id: int, item_id: int,
                   db=Depends(get_podcast_database)):
    django_microservice_response = await django_client.get_item(channel_id, item_id, request)
    response.status_code = django_microservice_response.status_code
    data = django_microservice_response.json()
    print("1" * 100)
    print(data)
    user_id = await find_user(request)
    if response.status_code == 200:
        refined_data = {k: v for k, v in data.items() if k not in ["seconds_listened"]}
        refined_data["is_bookmarked"], refined_data["bookmark_count"] = await check_episode_bookmark(user_id,
                                                                                                     channel_id,
                                                                                                     item_id, db)
        refined_data["is_liked"], refined_data["liked_count"] = await check_episode_like(user_id, channel_id,
                                                                                         item_id, db)

        data = refined_data
    return data


@routers.get("/like/{channel_id}/{item_id}/", status_code=status.HTTP_200_OK)
async def like(channel_id: int, item_id: int, db=Depends(get_podcast_database),
               payload: dict = Depends(get_access_jwt_aut())):
    user_collection = db["users"]
    podcast_collection = db["podcast"]

    user_id = payload["id"]

    user_filtering = {"user_id": user_id}
    channel_filtering = {"channel_id": channel_id}
    # channel_filtering = {"channel_id": channel_id, "episode": {"$elemMatch": {"episode_id": item_id}}}

    user_doc = {"$pull": {"liked": item_id}}
    channel_doc = {"$pull": {f"episode.{item_id}.likes": user_id}}
    # channel_doc = {"$pull": {f"episode.{item_id}.likes": user_id}}

    data = await user_collection.update_one(filter=user_filtering, update=user_doc, upsert=True)
    await podcast_collection.update_one(filter=channel_filtering, update=channel_doc, upsert=True)

    if data.modified_count == 0:
        user_doc = {"$push": {"liked": item_id}}
        channel_doc = {"$push": {f"episode.{item_id}.likes": user_id}}
        # channel_doc = {"$push": {f"episode.{item_id}.likes": user_id}}

        await user_collection.update_one(filter=user_filtering, update=user_doc, upsert=True)
        await podcast_collection.update_one(filter=channel_filtering, update=channel_doc, upsert=True)

        return {"liked done"}

    return {"unliked done"}


@routers.get("/bookmark_channel/{channel_id}/", status_code=status.HTTP_200_OK)
async def bookmark_channel(channel_id: int,
                           db=Depends(get_podcast_database),
                           payload: dict = Depends(get_access_jwt_aut())):
    user_collection = db["users"]
    podcast_collection = db["podcast"]

    user_id = payload["id"]

    user_filtering = {"user_id": user_id}
    channel_filtering = {"channel_id": channel_id}

    user_doc = {"$pull": {"channel_bookmark": channel_id}}
    channel_doc = {"$pull": {"channel_bookmark": user_id}}

    data = await user_collection.update_one(filter=user_filtering, update=user_doc, upsert=True)
    await podcast_collection.update_one(filter=channel_filtering, update=channel_doc, upsert=True)

    if data.modified_count == 0:
        user_doc = {"$push": {"channel_bookmark": channel_id}}
        channel_doc = {"$push": {"channel_bookmark": user_id}}

        await user_collection.update_one(filter=user_filtering, update=user_doc, upsert=True)
        await podcast_collection.update_one(filter=channel_filtering, update=channel_doc, upsert=True)
        return {"bookmark done"}

    return {"bookmark undone"}


@routers.get("/bookmark_episode/{channel_id}/{item_id}", status_code=status.HTTP_200_OK)
async def bookmark_episode(channel_id: int, item_id: int,
                           db=Depends(get_podcast_database),
                           payload: dict = Depends(get_access_jwt_aut())):
    user_collection = db["users"]
    podcast_collection = db["podcast"]

    user_id = payload["id"]

    user_filtering = {"user_id": user_id}
    channel_filtering = {"channel_id": channel_id}

    user_doc = {"$pull": {"episode_bookmark": item_id}}
    channel_doc = {"$pull": {f"episode.{item_id}.bookmarks": user_id}}

    data = await user_collection.update_one(filter=user_filtering, update=user_doc, upsert=True)
    await podcast_collection.update_one(filter=channel_filtering, update=channel_doc, upsert=True)

    if data.modified_count == 0:
        user_doc = {"$push": {"episode_bookmark": item_id}}
        channel_doc = {"$push": {f"episode.{item_id}.bookmarks": user_id}}

        await user_collection.update_one(filter=user_filtering, update=user_doc, upsert=True)
        await podcast_collection.update_one(filter=channel_filtering, update=channel_doc, upsert=True)
        return {"bookmark done"}

    return {"bookmark undone"}


@routers.post("/create_comment/{channel_id}/{item_id}/", status_code=status.HTTP_201_CREATED)
async def create_comment(channel_id: int, item_id: int, comment: Comment,
                         db=Depends(get_podcast_database),
                         payload: dict = Depends(get_access_jwt_aut())):
    user_collection = db["users"]
    podcast_collection = db["podcast"]

    user_id = payload["id"]
    user_email = payload["email"]

    user_filtering = {"user_id": user_id}
    channel_filtering = {"channel_id": channel_id}
    d = datetime.strptime(datetime.now(tz).isoformat(), "%Y-%m-%dT%H:%M:%S.%f+03:30")
    user_doc = {"$push": {"comment": {f"{item_id}": [d, comment.content, 0, 0]}}}
    channel_doc = {
        "$push": {f"episode.{item_id}.comment": {f'{uuid4().hex}': [f"{user_email}", d, comment.content, 0, 0]}}}

    await user_collection.update_one(filter=user_filtering, update=user_doc, upsert=True)
    await podcast_collection.update_one(filter=channel_filtering, update=channel_doc, upsert=True)
    return {"comment created"}


@routers.get("/comments_list/{channel_id}/{item_id}/", status_code=status.HTTP_200_OK)
async def comments_list(channel_id: int, item_id: int,
                        db=Depends(get_podcast_database),
                        _: dict = Depends(get_access_jwt_aut())):
    podcast_collection = db["podcast"]
    podcast_filtering = {"channel_id": channel_id}
    data = await podcast_collection.find_one(filter=podcast_filtering)
    if data:
        return data["episode"][f"{item_id}"]["comment"]
    return {"no comments"}



