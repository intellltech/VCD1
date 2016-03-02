package cmd

import (
	"fmt"
	"os"

	"github.com/ClusterHQ/dvol/pkg/datalayer"
	"github.com/spf13/cobra"
)

var basePath string
var echoTimes int
var disableDockerIntegration bool

const DEFAULT_BRANCH string = "master"

var RootCmd = &cobra.Command{
	Use:   "dvol",
	Short: "dvol is a version control system for your development data in Docker",
	Long: `dvol
====
dvol lets you commit, reset and branch the containerized databases
running on your laptop so you can easily save a particular state
and come back to it later.`,
}

var cmdSwitch = &cobra.Command{
	Use:   "switch",
	Short: "Switch active volume for commands below (commit, log etc)",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) == 0 {
			fmt.Println("Please specify a volume name.")
			os.Exit(1)
		}
		if len(args) > 1 {
			fmt.Println("Wrong number of arguments.")
			os.Exit(1)
		}
		volumeName := args[0]
		if !datalayer.ValidVolumeName(volumeName) {
			fmt.Println("Error: " + volumeName + " is not a valid name")
			os.Exit(1)
		}
		if !datalayer.VolumeExists(basePath, volumeName) {
			fmt.Println("Error: " + volumeName + " does not exist")
			os.Exit(1)
		}
		err := datalayer.SwitchVolume(basePath, volumeName)
		if err != nil {
			fmt.Println("Error switching volume")
			os.Exit(1)
		}
	},
}

func init() {
	// cobra.OnInitialize(initConfig)
	// TODO support: dvol -p <custom_path> init <volume_name>
	RootCmd.AddCommand(NewCmdInit())
	RootCmd.AddCommand(NewCmdRm(os.Stdout))
	RootCmd.AddCommand(cmdSwitch)

	RootCmd.PersistentFlags().StringVarP(&basePath, "path", "p", "/var/lib/dvol/volumes",
		"The name of the directory to use")
	RootCmd.PersistentFlags().BoolVar(&disableDockerIntegration,
		"disable-docker-integration", false, "Do not attempt to list/stop/start"+
			" docker containers which are using dvol volumes")
}
