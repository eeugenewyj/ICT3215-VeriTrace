class VeriTraceError(Exception):
    code = "veritrace_error"


class InputError(VeriTraceError):
    code = "invalid_input"


class IntegrityError(VeriTraceError):
    code = "integrity_error"


class DependencyError(VeriTraceError):
    code = "dependency_error"


class ParserError(VeriTraceError):
    code = "parser_error"


class ModelError(VeriTraceError):
    code = "model_error"


class ContextLimitError(ModelError):
    code = "context_limit"


class WorkflowError(VeriTraceError):
    code = "workflow_error"


class CitationError(VeriTraceError):
    code = "citation_error"
