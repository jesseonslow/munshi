from fastapi import APIRouter, Depends
from munshi_api.config import ApiConfig
from munshi_api.models.audit import GraphHealthReport, SourceMismatchReport
from munshi_api.services.graph_auditor import GraphAuditorEngine

router = APIRouter(prefix="/api/audit", tags=["Graph Audits"])


def get_auditor_engine():
    config = ApiConfig()
    return GraphAuditorEngine(config.wiki_dir, config.sources_dir)


@router.get("/health", response_model=GraphHealthReport)
def get_health_report(engine: GraphAuditorEngine = Depends(get_auditor_engine)):
    return engine.run_health_audit()


@router.get("/sources", response_model=list[SourceMismatchReport])
def audit_sources(engine: GraphAuditorEngine = Depends(get_auditor_engine)):
    return engine.audit_source_paths()


@router.get("/attributions")
def audit_attributions(engine: GraphAuditorEngine = Depends(get_auditor_engine)):
    return engine.audit_author_attributions()