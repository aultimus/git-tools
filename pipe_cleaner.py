#!/usr/bin/env python3

"""
This script is designed to report on the commits between two specified git refs
The original use case was to report on the staleness of release branches.
"""

import argparse
import datetime
import os
import subprocess
import sys

from collections import Counter

GIT_COMMIT_FIELDS = ['id', 'author_name', 'author_email', 'date', 'message']
GIT_LOG_FORMAT = ['%H', '%an', '%ae', '%at', '%s']
GIT_LOG_FORMAT = '%x1f'.join(GIT_LOG_FORMAT) + '%x1e'
LOG_CMD = 'git log --format="%s"' % GIT_LOG_FORMAT


class Details:

    def __init__(self, repo, branch, d):
        self.repo = repo
        self.branch = branch
        self.counter, self.oldest_commit = analyse_commits(d)

    def total(self):
        return sum(self.counter.values())

    def __str__(self):
        s = "%s %s\n" % (self.repo, self.branch)
        s += "%d commits outstanding, oldest is from %s\n" % (
            self.total(), self.oldest_commit.strftime("%d-%m-%Y"))
        s += "%s\n" % str(self.counter.most_common())
        return s


def unix_to_datetime(s):
    return datetime.datetime.fromtimestamp(int(s))


def analyse_commits(commit_list):
    # we do fancy date checking as the last commit output by git log is not
    # always guaranteed to be the oldest due to non-linear history
    author_count = Counter()
    oldest_date = datetime.datetime.now()
    for d in commit_list:
        author_count[d["author_name"]] += 1
        this_date = unix_to_datetime(d["date"])
        if this_date < oldest_date:
            oldest_date = this_date
    return author_count, oldest_date


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--repo-dir",
                        help="a directory to parse for git repositories to analyse")
    parser.add_argument("-b", "--branches", action="append",
                        help="""git refs to analyse in a..b pattern, option\
                        can be specified multiple times to analyse multiple branches""")
    # see https://stackoverflow.com/questions/462974/what-are-the-differences-between-double-dot-and-triple-dot-in-git-com
    # for discussion of .. notation
    parser.add_argument("-g", "--git-flags", action="append",
                        help="""flags to run git log with, e.g. --no-merges or --cherry-pick\
                        note to escape -- use -g=--no-merges rather than -g --no-merges""")
    parser.add_argument("-r", "--repo", action="append",
                        help="""path to a git repo to analyse, can be specified multiple times\
                        to analyse multiple repos""")

    args = parser.parse_args()

    if args.repo_dir is None and args.repo is None or args.branches is None:
        parser.print_help()
        sys.exit(1)

    # print(args.repo_dir)
    # print(args.branches)

    details_list = []
    repos = []
    if args.repo_dir is not None:
        repos.extend([args.repo_dir + os.path.sep + f
                      for f in os.listdir(args.repo_dir) if os.path.isdir(args.repo_dir)])

    if args.repo is not None:
        for repo in args.repo:
            abs_repo = os.path.abspath(repo)
            if os.path.isdir(abs_repo):
                repos.append(abs_repo)

    for repo in repos:
        for branch in args.branches:
            os.chdir(repo)
            branch_cmd = LOG_CMD + " " + branch
            if args.git_flags:
                branch_cmd = branch_cmd + " " + " ".join(args.git_flags)
            # print(branch_cmd)
            try:
                output = subprocess.check_output(branch_cmd, shell=True,
                                                 stderr=subprocess.STDOUT)
                output = output.decode("utf-8")
                if output.startswith("fatal: ambiguous argument"):
                    print("repo %s doesn't have branches %s" %
                          os.path.basename(repo), branch)
                    continue

                if output != "":
                    output = output.strip('\n\x1e').split("\x1e")
                    output = [row.strip().split("\x1f") for row in output]
                    # print(output)
                    d = [dict(zip(GIT_COMMIT_FIELDS, row)) for row in output]
                    # print(d)
                    details = Details(os.path.basename(repo), branch, d)
                    details_list.append(details)

            except subprocess.CalledProcessError as e:
                pass
                # print("error (likely no such branch exists)")
                # print()
                # print("subprocess ret %d" % e.returncode)
                # print(e.output.decode("utf-8")))

    details_list.sort(key=lambda x: x.total(), reverse=True)
    for d in details_list:
        print(d)


if __name__ == "__main__":
    main()
