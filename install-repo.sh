#! /bin/bash

if [ ! -d "~/bin/repo" ]; then
	mkdir ~/bin
	export PATH=~/bin:$PATH

	curl https://storage.googleapis.com/git-repo-downloads/repo > ~/bin/repo
	chmod a+x ~/bin/repo
fi
