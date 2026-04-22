from litestar import Response
from litestar.handlers import post
from litestar.params import Body
from litestar.controller import Controller

from typing import Annotated

from gemini.api.germplasm_resolver import resolve_germplasm
from gemini.api.accession import Accession
from gemini.api.line import Line
from gemini.db.models.accession_aliases import AccessionAliasModel
from gemini.rest_api.models import (
    ResolveRequest,
    ResolveResponse,
    ResolveResultOutput,
    AliasBulkRequest,
    AliasBulkResponse,
    AliasBulkError,
    RESTAPIError,
)


class GermplasmResolverController(Controller):

    @post(path="/resolve", sync_to_thread=True)
    def resolve(self, data: Annotated[ResolveRequest, Body]) -> ResolveResponse:
        try:
            hits = resolve_germplasm(
                names=data.names,
                experiment_id=data.experiment_id,
            )
            return ResolveResponse(
                results=[
                    ResolveResultOutput(
                        input_name=h.input_name,
                        match_kind=h.match_kind,
                        accession_id=h.accession_id,
                        line_id=h.line_id,
                        canonical_name=h.canonical_name,
                        candidates=[],
                    )
                    for h in hits
                ]
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description=""),
                status_code=500,
            )

    @post(path="/aliases/bulk", sync_to_thread=True)
    def bulk_aliases(self, data: Annotated[AliasBulkRequest, Body]) -> AliasBulkResponse:
        try:
            if data.scope not in ("global", "experiment"):
                return Response(
                    content=RESTAPIError(
                        error="Invalid scope",
                        error_description="scope must be 'global' or 'experiment'",
                    ),
                    status_code=400,
                )
            if (data.scope == "experiment") != (data.experiment_id is not None):
                return Response(
                    content=RESTAPIError(
                        error="Invalid scope/experiment_id combination",
                        error_description="experiment_id is required iff scope='experiment'",
                    ),
                    status_code=400,
                )

            created = 0
            updated = 0
            errors: list[AliasBulkError] = []

            for idx, entry in enumerate(data.entries):
                try:
                    if bool(entry.accession_name) == bool(entry.line_name):
                        errors.append(AliasBulkError(
                            index=idx,
                            alias=entry.alias,
                            reason="Exactly one of accession_name or line_name must be set",
                        ))
                        continue

                    accession_id = None
                    line_id = None
                    if entry.accession_name:
                        target = Accession.get(accession_name=entry.accession_name)
                        if not target:
                            errors.append(AliasBulkError(
                                index=idx, alias=entry.alias,
                                reason=f"Accession not found: {entry.accession_name}",
                            ))
                            continue
                        accession_id = target.id
                    else:
                        target = Line.get(line_name=entry.line_name)
                        if not target:
                            errors.append(AliasBulkError(
                                index=idx, alias=entry.alias,
                                reason=f"Line not found: {entry.line_name}",
                            ))
                            continue
                        line_id = target.id

                    existing = AccessionAliasModel.get_by_parameters(
                        alias=entry.alias,
                        scope=data.scope,
                        **({"experiment_id": data.experiment_id} if data.experiment_id else {}),
                    )

                    if existing:
                        same_target = (
                            (accession_id is not None and str(existing.accession_id) == str(accession_id))
                            or (line_id is not None and str(existing.line_id) == str(line_id))
                        )
                        if same_target:
                            if entry.source and existing.source != entry.source:
                                AccessionAliasModel.update(existing, source=entry.source)
                                updated += 1
                            continue
                        errors.append(AliasBulkError(
                            index=idx, alias=entry.alias,
                            reason="Alias already exists with a different target in this scope",
                        ))
                        continue

                    AccessionAliasModel.create(
                        alias=entry.alias,
                        accession_id=accession_id,
                        line_id=line_id,
                        scope=data.scope,
                        experiment_id=data.experiment_id,
                        source=entry.source,
                        alias_info={},
                    )
                    created += 1
                except Exception as row_e:
                    errors.append(AliasBulkError(
                        index=idx, alias=entry.alias, reason=str(row_e)
                    ))

            return AliasBulkResponse(created=created, updated=updated, errors=errors)
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description=""),
                status_code=500,
            )
