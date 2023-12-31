from datetime import datetime
from uuid import uuid4

import pytz
from fastapi import APIRouter, Depends, status, Request, Response

from config.jwt_authentication import get_access_jwt_aut
from db.mongodb import get_podcast_database
from schemas.interactions import Comment
from services.django_microservice import get_django_client
from utils.user import find_user, check_channel_bookmark, check_episode_like, check_episode_bookmark, get_users_list

tz = pytz.timezone("Asia/Tehran")
django_client = get_django_client()
routers = APIRouter(prefix="/v1")


@routers.get("/channel_list/")
async def channel_list(request: Request, response: Response, page: str | None = None, db=Depends(get_podcast_database)):
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
    user_id = payload["id"]

    data = await db["users"].update_one(filter={"user_id": user_id},
                                        update={"$pull": {"liked": f"{channel_id}_{item_id}"}}, upsert=True)
    await db["podcast"].update_one(filter={"channel_id": channel_id},
                                   update={"$pull": {f"episode.{item_id}.likes": user_id}}, upsert=True)

    if data.modified_count == 0:
        await db["users"].update_one(filter={"user_id": user_id},
                                     update={"$push": {"liked": f"{channel_id}_{item_id}"}}, upsert=True)
        await db["podcast"].update_one(filter={"channel_id": channel_id},
                                       update={"$push": {f"episode.{item_id}.likes": user_id}}, upsert=True)

        return {"liked done"}

    return {"unliked done"}


@routers.get("/bookmark_channel/{channel_id}/", status_code=status.HTTP_200_OK)
async def bookmark_channel(channel_id: int,
                           db=Depends(get_podcast_database),
                           payload: dict = Depends(get_access_jwt_aut())):
    user_id = payload["id"]

    data = await db["users"].update_one(filter={"user_id": user_id}, update={"$pull": {"channel_bookmark": channel_id}},
                                        upsert=True)
    await db["podcast"].update_one(filter={"channel_id": channel_id}, update={"$pull": {"channel_bookmark": user_id}},
                                   upsert=True)

    if data.modified_count == 0:
        await db["users"].update_one(filter={"user_id": user_id}, update={"$push": {"channel_bookmark": channel_id}},
                                     upsert=True)
        await db["podcast"].update_one(filter={"channel_id": channel_id},
                                       update={"$push": {"channel_bookmark": user_id}}, upsert=True)
        return {"bookmark done"}

    return {"bookmark undone"}


@routers.get("/bookmark_episode/{channel_id}/{item_id}", status_code=status.HTTP_200_OK)
async def bookmark_episode(channel_id: int, item_id: int,
                           db=Depends(get_podcast_database),
                           payload: dict = Depends(get_access_jwt_aut())):
    user_id = payload["id"]

    data = await db["users"].update_one(filter={"user_id": user_id},
                                        update={"$pull": {"episode_bookmark": f"{channel_id}_{item_id}"}},
                                        upsert=True)
    await db["podcast"].update_one(filter={"channel_id": channel_id},
                                   update={"$pull": {f"episode.{item_id}.bookmarks": user_id}},
                                   upsert=True)

    if data.modified_count == 0:
        await db["users"].update_one(filter={"user_id": user_id},
                                     update={"$push": {"episode_bookmark": f"{channel_id}_{item_id}"}},
                                     upsert=True)
        await db["podcast"].update_one(filter={"channel_id": channel_id},
                                       update={"$push": {f"episode.{item_id}.bookmarks": user_id}},
                                       upsert=True)
        return {"bookmark done"}

    return {"bookmark undone"}


@routers.post("/create_comment/{channel_id}/{item_id}/", status_code=status.HTTP_201_CREATED)
async def create_comment(channel_id: int, item_id: int, comment: Comment,
                         db=Depends(get_podcast_database),
                         payload: dict = Depends(get_access_jwt_aut())):
    user_id = payload["id"]
    user_email = payload["email"]

    d = datetime.strptime(datetime.now(tz).isoformat(), "%Y-%m-%dT%H:%M:%S.%f+03:30")

    user_doc = {"$push": {"comment": {f"{item_id}": [d, comment.content, 0, 0]}}}
    channel_doc = {
        "$push": {f"episode.{item_id}.comment": {f'{uuid4().hex}': [f"{user_email}", d, comment.content, 0, 0]}}}

    await db["users"].update_one(filter={"user_id": user_id}, update=user_doc, upsert=True)
    await db["podcast"].update_one(filter={"channel_id": channel_id}, update=channel_doc, upsert=True)
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


@routers.get("/users_bookmarked_channel/{channel_id}/", status_code=status.HTTP_200_OK)
async def users_bookmarked_channel(channel_id: str, db=Depends(get_podcast_database)):
    user_list = await get_users_list(int(channel_id), db)
    return user_list


@routers.get("/user_liked_episode_list/", status_code=status.HTTP_200_OK)
async def user_liked_episode_list(db=Depends(get_podcast_database),
                                  payload: dict = Depends(get_access_jwt_aut())):
    user_id = payload["id"]
    data = await db["users"].find_one({"user_id": user_id}, {"_id": 0, "liked": 1})
    return data


@routers.get("/user_channel_bookmark_list/", status_code=status.HTTP_200_OK)
async def user_channel_bookmark_list(db=Depends(get_podcast_database),
                                     payload: dict = Depends(get_access_jwt_aut())):
    user_id = payload["id"]
    data = await db["users"].find_one({"user_id": user_id}, {"_id": 0, "channel_bookmark": 1})
    return data


@routers.get("/user_episode_bookmark_list/", status_code=status.HTTP_200_OK)
async def user_episode_bookmark_list(db=Depends(get_podcast_database),
                                     payload: dict = Depends(get_access_jwt_aut())):
    user_id = payload["id"]
    data = await db["users"].find_one({"user_id": user_id}, {"_id": 0, "episode_bookmark": 1})
    return data
