package main

import (
	"fmt"
	"io"
	"log"
	"net"

	"github.com/vmihailenco/msgpack/v5"
)

const listenAddress = "127.0.0.1:30120"

type ClientMessage struct {
	Type     string `msgpack:"type"`
	Username string `msgpack:"username"`
}

type ServerMessage struct {
	Type       string `msgpack:"type"`
	ServerName string `msgpack:"server_name"`
	Message    string `msgpack:"message"`
}

func handleClient(conn net.Conn) {
	defer conn.Close()

	remoteAddr := conn.RemoteAddr().String()
	log.Printf("Client connected: %s", remoteAddr)

	decoder := msgpack.NewDecoder(conn)

	for {
		var msg ClientMessage

		err := decoder.Decode(&msg)
		if err != nil {
			if err == io.EOF {
				log.Printf("Client disconnected: %s", remoteAddr)
				return
			}

			log.Printf("Client error from %s: %v", remoteAddr, err)
			return
		}

		switch msg.Type {
		case "hello":
			log.Printf("Player joined: %s from %s", msg.Username, remoteAddr)

			welcome := ServerMessage{
				Type:       "welcome",
				ServerName: "BreathM Development Server",
				Message:    "Welcome to BreathM",
			}

			if err := msgpack.NewEncoder(conn).Encode(welcome); err != nil {
				log.Printf("Failed to send welcome to %s: %v", remoteAddr, err)
				return
			}
		default:
			log.Printf("Unknown message from %s: %+v", remoteAddr, msg)
		}
	}
}

func main() {
	listener, err := net.Listen("tcp", listenAddress)
	if err != nil {
		log.Fatalf("Failed to start BreathM server: %v", err)
	}
	defer listener.Close()

	fmt.Printf("BreathM server listening on %s\n", listenAddress)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Accept error: %v", err)
			continue
		}

		go handleClient(conn)
	}
}
