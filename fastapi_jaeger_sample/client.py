import grpc
import hello_pb2
import hello_pb2_grpc

def run():
    # Connect to your local server on port 50051
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = hello_pb2_grpc.GreeterStub(channel)
        # Make the SayHello RPC
        response = stub.SayHello(hello_pb2.HelloRequest(name="Sankalp"))
        print(f"Greeter client received: {response.message}")

if __name__ == "__main__":
    run()
