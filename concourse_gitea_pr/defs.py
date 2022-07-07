from dataclasses import asdict, dataclass

from dateutil import parser


@dataclass
class PrResource:
    repo: str
    owner: str
    hostname: str
    access_token: str
    private_key: str

    @property
    def endpoint(self):
        return f"https://{self.hostname}/api/v1/repos/{self.owner}/{self.repo}"

    @property
    def uri(self):
        return f"git@{self.hostname}:{self.owner}/{self.repo}.git"


@dataclass
class PrVersion:
    number: int
    sha: str
    committed_at: str

    def __post_init__(self):
        self.committed_at_dt = parser.isoparse(self.committed_at)

    @property
    def output(self):
        d = asdict(self)
        d["number"] = str(d["number"])
        return d


@dataclass
class PrMetadata:
    number: int
    title: str
    base: str
    head: str
    created_at: str
    created_by: str

    @property
    def output(self):
        d = asdict(self)
        d["number"] = str(d["number"])
        return [{"name": k, "value": v} for k, v in d.items()]
