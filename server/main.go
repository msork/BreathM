package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"sort"
	"sync"

	"github.com/vmihailenco/msgpack/v5"
)

const listenAddress = "127.0.0.1:30120"

type ClientMessage struct {
	Type     string `msgpack:"type"`
	Username string `msgpack:"username"`
}

type ServerMessage struct {
	Type       string   `msgpack:"type"`
	ServerName string   `msgpack:"server_name,omitempty"`
	Message    string   `msgpack:"message,omitempty"`
	Players    []string `msgpack:"players,omitempty"`
	Event	   string   `msgpack:"event,omitempty"`
}

type Client struct {
	Conn     net.Conn
	Username string
	Encoder  *msgpack.Encoder
}

var (
	clients      = make(map[*Client]bool)
	clientsMutex sync.Mutex
)

func registerClient(client *Client) {
	clientsMutex.Lock()
	defer clientsMutex.Unlock()

	clients[client] = true
	log.Printf("Connected players: %d", len(clients))
}

func unregisterClient(client *Client) {
	clientsMutex.Lock()
	wasRegistered := clients[client]
	if wasRegistered {
		delete(clients, client)
	}
	clientsMutex.Unlock()

	if wasRegistered {
		log.Printf("Player left: %s", client.Username)
		broadcastPlayerList()
		broadcastEvent(fmt.Sprintf("%s left", client.Username))
	}
}

func connectedPlayerNames() []string {
	clientsMutex.Lock()
	defer clientsMutex.Unlock()

	players := make([]string, 0, len(clients))
	for client := range clients {
		if client.Username != "" {
			players = append(players, client.Username)
		}
	}

	sort.Strings(players)
	return players
}

func broadcastPlayerList() {
	players := connectedPlayerNames()
	message := ServerMessage{
		Type:    "player_list",
		Players: players,
	}

	clientsMutex.Lock()
	defer clientsMutex.Unlock()

	for client := range clients {
		if err := client.Encoder.Encode(message); err != nil {
			log.Printf("Failed to send player list to %s: %v", client.Username, err)
		}
	}
}

func broadcastEvent(event string) {
	message := ServerMessage{
		Type:  "event",
		Event: event,
	}

	clientsMutex.Lock()
	defer clientsMutex.Unlock()

	for client := range clients {
		if err := client.Encoder.Encode(message); err != nil {
			log.Printf("Failed to send event to %s: %v", client.Username, err)
		}
	}
}

func handleClient(conn net.Conn) {
	defer conn.Close()

	remoteAddr := conn.RemoteAddr().String()
	log.Printf("Client connected: %s", remoteAddr)

	client := &Client{
		Conn:    conn,
		Encoder: msgpack.NewEncoder(conn),
	}

	decoder := msgpack.NewDecoder(conn)
	registered := false

	defer func() {
		if registered {
			unregisterClient(client)
		}
		log.Printf("Client disconnected: %s", remoteAddr)
	}()

	for {
		var msg ClientMessage

		err := decoder.Decode(&msg)
		if err != nil {
			if err == io.EOF {
				return
			}

			log.Printf("Client error from %s: %v", remoteAddr, err)
			return
		}

		switch msg.Type {
		case "hello":
			client.Username = msg.Username
			log.Printf("Player joined: %s from %s", msg.Username, remoteAddr)

			if !registered {
				registerClient(client)
				registered = true
			}

			welcome := ServerMessage{
				Type:       "welcome",
				ServerName: "BreathM Development Server",
				Message:    "Welcome to BreathM",
			}

			if err := client.Encoder.Encode(welcome); err != nil {
				log.Printf("Failed to send welcome to %s: %v", remoteAddr, err)
				return
			}

			broadcastPlayerList()
			broadcastEvent(fmt.Sprintf("%s joined", msg.Username))
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
