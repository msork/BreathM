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
const protocolVersion = "alpha-0.5"

type ClientMessage struct {
	Type     string `msgpack:"type"`
	Username string `msgpack:"username"`
	Status   string `msgpack:"status"`
	ProtocolVersion string `msgpack:"protocol_version"`
}

type PlayerInfo struct {
	Username string `msgpack:"username"`
	Status   string `msgpack:"status"`
}

type ServerMessage struct {
	Type       string       `msgpack:"type"`
	ServerName string       `msgpack:"server_name,omitempty"`
	Message    string       `msgpack:"message,omitempty"`
	Players    []PlayerInfo `msgpack:"players,omitempty"`
	Event      string       `msgpack:"event,omitempty"`
	ProtocolVersion string `msgpack:"protocol_version,omitempty"`
}

type Client struct {
	Conn     net.Conn
	Username string
	Status   string
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

func connectedPlayers() []PlayerInfo {
	clientsMutex.Lock()
	defer clientsMutex.Unlock()

	players := make([]PlayerInfo, 0, len(clients))
	for client := range clients {
		if client.Username != "" {
			status := client.Status
			if status == "" {
				status = "launcher"
			}

			players = append(players, PlayerInfo{
				Username: client.Username,
				Status:   status,
			})
		}
	}

	sort.Slice(players, func(i, j int) bool {
		return players[i].Username < players[j].Username
	})

	return players
}

func broadcastPlayerList() {
	players := connectedPlayers()
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

func statusDisplayName(status string) string {
	switch status {
	case "in_game":
		return "In Game"
	default:
		return "In Launcher"
	}
}

func handleClient(conn net.Conn) {
	defer conn.Close()

	remoteAddr := conn.RemoteAddr().String()
	log.Printf("Client connected: %s", remoteAddr)

	client := &Client{
		Conn:    conn,
		Status:  "launcher",
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
			client.Status = "launcher"
			log.Printf("Player joined: %s from %s", msg.Username, remoteAddr)

			if msg.ProtocolVersion != protocolVersion {
				log.Printf("Rejected %s: incompatible protocol %s", remoteAddr, msg.ProtocolVersion)

				reject := ServerMessage{
					Type:            "error",
					Message:         "Incompatible BreathM protocol version",
					ProtocolVersion: protocolVersion,
				}

				_ = client.Encoder.Encode(reject)
				return
			}

			if !registered {
				registerClient(client)
				registered = true
			}

			welcome := ServerMessage{
				Type:       "welcome",
				ServerName: "BreathM Development Server",
				Message:    "Welcome to BreathM",
				ProtocolVersion: protocolVersion,
			}

			if err := client.Encoder.Encode(welcome); err != nil {
				log.Printf("Failed to send welcome to %s: %v", remoteAddr, err)
				return
			}

			broadcastPlayerList()
			broadcastEvent(fmt.Sprintf("%s joined", msg.Username))
		case "status":
			if !registered {
				log.Printf("Ignoring status from unregistered client %s", remoteAddr)
				continue
			}

			if msg.Status != "launcher" && msg.Status != "in_game" {
				log.Printf("Ignoring invalid status from %s: %s", client.Username, msg.Status)
				continue
			}

			if client.Status != msg.Status {
				client.Status = msg.Status
				log.Printf("Player status changed: %s -> %s", client.Username, msg.Status)
				broadcastPlayerList()
				broadcastEvent(fmt.Sprintf("%s is now %s", client.Username, statusDisplayName(msg.Status)))
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
