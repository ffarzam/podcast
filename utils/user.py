from config.jwt_authentication import AccessJWTBearer


async def check_channel_bookmark(user_id, channel_id, db):
    # user_collection = db["users"]
    podcast_collection = db["podcast"]

    data = await podcast_collection.find_one({"channel_id": channel_id, "channel_bookmark": {"$exists": True}},
                                             projection={"channel_bookmark": {"$elemMatch": {"$in": [user_id]}},
                                                         "count": {"$size": "$channel_bookmark"}})
    count = 0
    state = False
    if data:
        count = data.get("count", 0)
        state = bool(data.get("channel_bookmark"))

    return state, count


async def check_episode_like(user_id, channel_id, item_id, db):
    # user_collection = db["users"]
    podcast_collection = db["podcast"]

    count_data = await podcast_collection.find_one({"channel_id": channel_id},
                                                   projection={f"episode.{item_id}.likes": 1, "_id": 0})
    data = await podcast_collection.find_one({"channel_id": channel_id, f"episode.{item_id}.likes": {"$elemMatch": {
        "$in": [user_id]}}})

    # data1 = await podcast_collection.aggregate({"$match":{"episode.":}})

    count = 0
    if count_data and count_data.get("episode") and count_data.get("episode").get(f"{item_id}") and count_data.get(
            "episode").get(f"{item_id}").get("likes"):
        count = len(count_data.get("episode").get(f"{item_id}").get("likes"))
    return bool(data), count


async def check_episode_bookmark(user_id, channel_id, item_id, db):
    # user_collection = db["users"]
    podcast_collection = db["podcast"]
    count_data = await podcast_collection.find_one({"channel_id": channel_id},
                                                   projection={f"episode.{item_id}.bookmarks": 1, "_id": 0})
    data = await podcast_collection.find_one({"channel_id": channel_id, f"episode.{item_id}.bookmarks": {"$elemMatch": {
        "$in": [user_id]}}})

    count = 0
    if count_data and count_data.get("episode") and count_data.get("episode").get(f"{item_id}") and count_data.get(
            "episode").get(f"{item_id}").get("bookmarks"):
        count = len(count_data.get("episode").get(f"{item_id}").get("bookmarks"))
    return bool(data), count


async def find_user(request):
    user_id = None
    try:
        payload = await AccessJWTBearer()(request)
        user_id = payload["id"]
    except Exception:
        pass
    return user_id
