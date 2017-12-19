package main

import (
	"flag"
	"fmt"
	"os/exec"
	"strings"

	"github.com/nlopes/slack"
)

func runScript(cmd string, args []string) (string, error) {
	b, err := exec.Command(cmd, args...).Output()
	return string(b), err
}

// roadmap
// v0 - can dump "foobar" on mention
// v1 - can dump program output on mention
// v2 - dumps program output at time specified by flag everyday

func main() {
	var token = flag.String("token", "", "slack api token")
	var botID = flag.String("bot-id", "U8HV269AT", "id of bot in order to detect mentions")
	var cmdStr = flag.String("cmd", "echo foo bar cat", "command to be run including args")

	//var monitorChannel = flag.String("monitor-channel", "backend",
	//	"channel to monitor for mentions / to post to")

	flag.Parse()

	fmt.Printf("using cmd [%s]\n", *cmdStr)

	if *token == "" {
		panic("no token provided")
	}

	var cmd string
	var args []string
	for i, v := range strings.Split(*cmdStr, " ") {
		if i == 0 {
			cmd = v
		} else {
			args = append(args, v)
		}
	}

	// start a websocket-based Real Time API session
	api := slack.New(*token)
	//api.SetDebug(true)
	rtm := api.NewRTM()

	go rtm.ManageConnection()

	fmt.Println("slackbot ready, ^C exits")

	// perhaps should spawn new requests in a new goro
	for msg := range rtm.IncomingEvents {
		if msg.Type == "message" {
			//spew.Dump(msg)
			d := msg.Data.(*slack.MessageEvent)
			channel := d.Msg.Channel
			fmt.Println(d.Text)
			// TODO: cant quite work out how to get user id to check mentions
			mentionStr := fmt.Sprintf("<@%s>", *botID)
			if strings.Index(d.Text, mentionStr) == -1 {
				// we weren't mentioned
				fmt.Println("no mention")
				continue
			}
			scriptOutput, err := runScript(cmd, args)
			if err != nil {
				// should be graceful?
				panic(err)
			}
			_, _, err = api.PostMessage(channel, "bleep bloop bloop",
				slack.PostMessageParameters{
					Attachments: []slack.Attachment{slack.Attachment{Text: scriptOutput}},
					Text:        scriptOutput,
				})

			if err != nil {
				// should be graceful?
				panic(err)
			}

		}
	}
}
