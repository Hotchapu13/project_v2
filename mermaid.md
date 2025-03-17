# Distributed System Mermaid Diagrams

This document contains Mermaid diagrams that explain the architecture and flow of the bidirectional client-server system.

## System Architecture

```mermaid
graph TB
    subgraph Client
        C_UI[User Interface]
        C_Sender[Sender]
        C_Receiver[Receiver]
        C_File[File Handler]
    end
    
    subgraph Server
        S_Handler[Client Handler]
        S_Sender[Sender]
        S_Receiver[Receiver]
        S_File[File Handler]
    end
    
    C_UI -->|User Input| C_Sender
    C_Sender -->|Messages/Files| S_Receiver
    S_Receiver -->|Process| S_Handler
    S_Handler -->|Response| S_Sender
    S_Sender -->|Messages/Files| C_Receiver
    C_Receiver -->|Display| C_UI
    
    C_Sender -->|File Operations| C_File
    S_Sender -->|File Operations| S_File
```

## Protocol Structure

```mermaid
graph TD
    Start[Message Type] --> MessageType{Type?}
    MessageType -->|"MSG:"| MessageContent[Message Content]
    MessageType -->|"FILE:"| FileName[Filename]
    FileName --> FileContent[File Chunks]
    FileContent --> EOF["ENDOFFILE" Marker]
```

## Client Flow Diagram

```mermaid
flowchart TD
    Start[Start Client] --> Connect[Connect to Server]
    Connect --> CreateTasks[Create Sender/Receiver Tasks]
    
    subgraph Sender Task
        SenderStart[Start Sender] --> GetUserInput[Get User Input]
        GetUserInput --> CheckInput{Input Type?}
        CheckInput -->|Normal Message| SendMessage[Send "MSG:" + message]
        CheckInput -->|Send File Command| GetFilename[Get Filename]
        GetFilename --> CheckFileExists{File Exists?}
        CheckFileExists -->|Yes| SendFileHeader[Send "FILE:" + filename]
        SendFileHeader --> SendFileChunks[Send File in Chunks]
        SendFileChunks --> SendEOF[Send ENDOFFILE marker]
        CheckFileExists -->|No| FileNotFound[Show "File not found"]
        FileNotFound --> GetUserInput
        CheckInput -->|Exit Command| BreakLoop[Exit Loop]
        SendMessage --> GetUserInput
        SendEOF --> GetUserInput
    end
    
    subgraph Receiver Task
        ReceiverStart[Start Receiver] --> ReadData[Read Data from Server]
        ReadData --> CheckData{Data Type?}
        CheckData -->|"MSG:"| DisplayMessage[Display Message]
        CheckData -->|"FILE:"| ExtractFilename[Extract Filename]
        ExtractFilename --> CreateFile[Create File]
        CreateFile --> ReceiveChunks[Receive File Chunks]
        ReceiveChunks --> CheckForEOF{End of File?}
        CheckForEOF -->|No| ReceiveChunks
        CheckForEOF -->|Yes| SaveFile[Save File]
        DisplayMessage --> ReadData
        SaveFile --> ReadData
        CheckData -->|No Data| ConnectionClosed[Connection Closed]
    end
    
    CreateTasks --> WaitForCompletion[Wait for Tasks Completion]
    WaitForCompletion --> CleanUp[Clean Up and Close Connection]
    CleanUp --> End[End Client]
```

## Server Flow Diagram

```mermaid
flowchart TD
    Start[Start Server] --> CreateServer[Create Server on Port 12345]
    CreateServer --> WaitForConnections[Wait for Client Connections]
    WaitForConnections --> ClientConnects[Client Connects]
    ClientConnects --> HandleClient[Handle Client]
    HandleClient --> CreateTasks[Create Sender/Receiver Tasks for Client]
    
    subgraph Client Handler
        subgraph Sender Task
            SenderStart[Start Sender] --> GetServerInput[Get Server Input]
            GetServerInput --> CheckInput{Input Type?}
            CheckInput -->|Normal Message| SendMessage[Send "MSG:" + message]
            CheckInput -->|Send File Command| GetFilename[Get Filename]
            GetFilename --> CheckFileExists{File Exists?}
            CheckFileExists -->|Yes| SendFileHeader[Send "FILE:" + filename]
            SendFileHeader --> SendFileChunks[Send File in Chunks]
            SendFileChunks --> SendEOF[Send ENDOFFILE marker]
            CheckFileExists -->|No| FileNotFound[Show "File not found"]
            FileNotFound --> GetServerInput
            CheckInput -->|Exit Command| SendExitMessage[Send Exit Message]
            SendExitMessage --> BreakLoop[Exit Loop]
            SendMessage --> GetServerInput
            SendEOF --> GetServerInput
        end
        
        subgraph Receiver Task
            ReceiverStart[Start Receiver] --> ReadData[Read Data from Client]
            ReadData --> CheckData{Data Type?}
            CheckData -->|"MSG:"| DisplayMessage[Display Message]
            CheckData -->|"FILE:"| ExtractFilename[Extract Filename]
            ExtractFilename --> CreateFile[Create File with "received_" prefix]
            CreateFile --> ReceiveChunks[Receive File Chunks]
            ReceiveChunks --> CheckForEOF{End of File?}
            CheckForEOF -->|No| ReceiveChunks
            CheckForEOF -->|Yes| SaveFile[Save File]
            DisplayMessage --> ReadData
            SaveFile --> ReadData
            CheckData -->|No Data| ClientDisconnected[Client Disconnected]
            ClientDisconnected --> ExitReceiver[Exit Receiver]
        end
    end
    
    CreateTasks --> WaitForTasksCompletion[Wait for Tasks Completion]
    WaitForTasksCompletion --> CleanUp[Clean Up and Close Connection]
    CleanUp --> WaitForConnections
```

## File Transfer Sequence Diagram

```mermaid
sequenceDiagram
    participant Sender
    participant Receiver
    
    Sender->>Receiver: FILE:filename\n
    loop For each chunk
        Sender->>Receiver: File chunk data
    end
    Sender->>Receiver: ENDOFFILE\n
    Note over Receiver: Save file as "received_filename"
```

## Code Structure

```mermaid
classDiagram
    class BiClient {
        SERVER_IP: str
        PORT: int
        BUFFER_SIZE: int
        +client(): async
        +sender(writer): async
        +receiver(reader): async
        +send_file(writer, filename): async
    }
    
    class BiServer {
        HOST: str
        PORT: int
        BUFFER_SIZE: int
        +main(): async
        +handle_client(reader, writer): async
        -sender(): async
        -receiver(): async
        -send_file(filename): async
    }
    
    BiClient ..> "uses" asyncio
    BiClient ..> "uses" aioconsole
    BiServer ..> "uses" asyncio
    BiServer ..> "uses" aioconsole
```

## System Communication Overview

```mermaid
graph LR
    subgraph Client Machine
        Client[biclient2.py]
    end
    
    subgraph Server Machine
        Server[biserver2.py]
    end
    
    Client -->|Send Messages/Files| Server
    Server -->|Send Messages/Files| Client
    
    Client -->|User Interaction| User1[Client User]
    Server -->|User Interaction| User2[Server Admin]
``` 