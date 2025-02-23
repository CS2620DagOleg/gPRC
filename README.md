## gPRC
gPRC chat implementation 


**How to run:** 
1. Install required packets if needed

pip install grpcio grpcio-tools


2. Generate gPRC stubs

python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chat.proto


3. Run the server

4. Run the client

