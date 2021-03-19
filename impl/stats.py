# =============================================================================
#
# EZID :: stats.py
#
# Identifier statistics.
#
# To avoid burdening online identifier processing, statistics are
# computed periodically by a daemon thread.  We eschew a synchronous,
# inline approach to maintaining statistics because identifier changes
# can be complex (creation times can change, ownership can change,
# even users and groups can change) and tracking the effects of those
# changes on statistics would require knowledge of an identifier's
# pre-change state, which is not recorded.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import datetime
import threading
import time
import uuid

import django.conf
import django.db
import django.db.models
import django.db.transaction

import ezidapp.models.search_identifier
import ezidapp.models.search_user
import ezidapp.models.statistics
import ezidapp.models.statistics
import ezidapp.models.statistics
import impl.config
import impl.log

_enabled = None
_computeCycle = None
_computeSameTimeOfDay = None
_threadName = None


def _sameTimeOfDayDelta():
    now = datetime.datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # noinspection PyTypeChecker
    d = _computeCycle - (now - midnight).total_seconds()
    if d < 0:
        d += 86400
    return d


def _timestampToMonth(t):
    return time.strftime("%Y-%m", time.localtime(t))


def _identifierType(id_str):
    return id_str.split(":")[0].upper()


def recomputeStatistics():
    """Recomputes and stores identifier statistics.

    The old statistics are completely replaced.
    """
    try:
        users = {
            u.id: (u.pid, u.group.pid, u.realm.name)
            for u in ezidapp.models.search_user.SearchUser.objects.all().select_related(
                "group", "realm"
            )
        }
        counts = {}
        lastIdentifier = ""
        while True:
            qs = (
                ezidapp.models.search_identifier.SearchIdentifier.objects.filter(
                    identifier__gt=lastIdentifier
                )
                .only("identifier", "owner_id", "createTime", "isTest", "hasMetadata")
                .order_by("identifier")
            )
            qs = list(qs[:1000])
            if len(qs) == 0:
                break
            for id_model in qs:
                if not id_model.isTest and id_model.owner_id in users:
                    t = (
                        _timestampToMonth(id_model.createTime),
                        id_model.owner_id,
                        _identifierType(id_model.identifier),
                        id_model.hasMetadata,
                    )
                    counts[t] = counts.get(t, 0) + 1
            lastIdentifier = qs[-1].identifier
        with django.db.transaction.atomic():
            ezidapp.models.statistics.Statistics.objects.all().delete()
            for t, v in list(counts.items()):
                c = ezidapp.models.statistics.Statistics(
                    month=t[0],
                    owner=users[t[1]][0],
                    ownergroup=users[t[1]][1],
                    realm=users[t[1]][2],
                    type=t[2],
                    hasMetadata=t[3],
                    count=v,
                )
                c.full_clean(validate_unique=False)
                c.save(force_insert=True)
    except Exception as e:
        impl.log.otherError("stats.recomputeStatistics", e)


def _statisticsDaemon():
    if _computeSameTimeOfDay:
        django.db.connections["default"].close()
        django.db.connections["search"].close()
        time.sleep(_sameTimeOfDayDelta())
    else:
        # We arbitrarily sleep 10 minutes to avoid putting a burden on the
        # server near startup or reload.
        time.sleep(600)
    while _enabled and threading.currentThread().getName() == _threadName:
        start = time.time()
        recomputeStatistics()
        django.db.connections["default"].close()
        django.db.connections["search"].close()
        if _computeSameTimeOfDay:
            time.sleep(_sameTimeOfDayDelta())
        else:
            # noinspection PyTypeChecker
            time.sleep(max(_computeCycle - (time.time() - start), 0))


def loadConfig():
    global _enabled, _computeCycle, _computeSameTimeOfDay, _threadName
    _enabled = (
        django.conf.settings.DAEMON_THREADS_ENABLED
        and django.conf.settings.DAEMONS_STATISTICS_ENABLED
    )
    if _enabled:
        _computeCycle = int(django.conf.settings.DAEMONS_STATISTICS_COMPUTE_CYCLE)
        _computeSameTimeOfDay = (
            django.conf.settings.DAEMONS_STATISTICS_COMPUTE_SAME_TIME_OF_DAY
        )
        _threadName = uuid.uuid1().hex
        t = threading.Thread(target=_statisticsDaemon, name=_threadName)
        t.setDaemon(True)
        t.start()


def query(
    month=None, owner=None, ownergroup=None, realm=None, type=None, hasMetadata=None
):
    """Returns the number of identifiers matching a constraint as defined by
    the non-None argument values.

    The arguments correspond to the fields in the Statistics model.
    """
    qs = ezidapp.models.statistics.Statistics.objects
    if month is not None:
        qs = qs.filter(month=month)
    if owner is not None:
        qs = qs.filter(owner=owner)
    if ownergroup is not None:
        qs = qs.filter(ownergroup=ownergroup)
    if realm is not None:
        qs = qs.filter(realm=realm)
    if type is not None:
        qs = qs.filter(type=type)
    if hasMetadata is not None:
        qs = qs.filter(hasMetadata=hasMetadata)
    return qs.aggregate(django.db.models.Sum("count"))["count__sum"] or 0


def getTable(owner=None, ownergroup=None, realm=None):
    """Returns a table (a list) of identifier counts ordered by month. Each
    element of the list is a pair.

      (month, { (type, hasMetadata): count, ... })

    For example:

       ("2016-01", { ("ARK", False): 14837, ("ARK", True): 1789,
         ("DOI", "True"): 11267 })

    In dictionaries zero counts are not represented, and thus
    dictionaries will not necessarily be complete with respect to the
    Cartesian product of identifier type and hasMetadata.  The range of
    months returned is determined by the range of nonzero counts, but
    within that range months are guaranteed to be consecutive.  Empty
    entries will resemble:

       ("2016-02", {})

    The table can optionally be limited by owner and/or group and/or
    realm.
    """
    qs = ezidapp.models.statistics.Statistics.objects
    if owner is None and ownergroup is None and realm is None:
        qs = qs.all()
    else:
        if owner is not None:
            qs = qs.filter(owner=owner)
        if ownergroup is not None:
            qs = qs.filter(ownergroup=ownergroup)
        if realm is not None:
            qs = qs.filter(realm=realm)
    counts = {}
    for c in qs:
        d = counts.get(c.month, {})
        dc = d.get((c.type, c.hasMetadata), 0)
        d[(c.type, c.hasMetadata)] = dc + c.count
        counts[c.month] = d

    def incrementMonth(month):
        y, m = [int(c) for c in month.split("-")]
        m += 1
        if m > 12:
            m = 1
            y += 1
        return f"{y:04d}-{m:02d}"

    table = []
    months = list(counts.keys())
    months.sort()
    for m in months:
        if m != months[0]:
            # noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
            nextM = incrementMonth(lastM)
            while nextM != m:
                table.append((nextM, {}))
                nextM = incrementMonth(nextM)
        table.append((m, counts[m]))
        lastM = m
    return table