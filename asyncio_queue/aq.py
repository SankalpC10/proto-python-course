from fastapi import FastAPI, Request
import asyncio
import uuid
import datetime

app = FastAPI()

queue = asyncio.Queue()


@app.post("/enqueue")
async def enqueue_request(request: Request):
    body = await request.body()

    request_id = str(uuid.uuid4())
    timestamp = asyncio.get_running_loop().time()

    await queue.put({
        "id": request_id,
        "timestamp": timestamp,
        "body": body
    })

    return {"status": "enqueued", "request_id": request_id}


async def process_queue():
    while True:
        item = await queue.get()
        try:
            start_time = asyncio.get_running_loop().time()
            request_id = item["id"]
            enqueue_time = item["timestamp"]

            queue_time = start_time - enqueue_time

            await asyncio.sleep(5)

            end_time = asyncio.get_running_loop().time()
            processing_time = end_time - start_time
            total_time = end_time - enqueue_time

            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

            print(
                f"[{current_time}] Request {request_id}: Queue time: {queue_time:.4f}s, Processing time: {processing_time:.4f}s, Total time: {total_time:.4f}s")
            # print(f"Body: {item['body'][:100]}..." if len(item['body']) > 100 else f"Body: {item['body']}")
        except Exception as e:
            print(f"Error processing item: {e}")
        finally:
            queue.task_done()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_queue())


@app.on_event("shutdown")
async def shutdown_event():
    if not queue.empty():
        await queue.join()


