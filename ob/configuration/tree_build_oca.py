from ob.comunication.request_solver import RequestSolver
from ob.comunication.router import Router
from ob.data_colection.base_components.tree_base_broker import TreeBaseBroker
from ob.data_colection.base_components.tree_base_broker_default_target import TreeBaseBrokerDefaultTarget
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_blocker_access_grantor import TreeBlockerAccessGrantor
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.data_colection.specialistic_components.tree_request_alpaca_blocker import TreeRequestAlpacaBlocker


def tree_build() -> Router:
    """This is the main ocabox tree structure for the "Observatorio Cerro Armazones" observatory.."""

    # --------------------------------------- wk06 ---------------------------------------
    alpaca_wk06 = TreeAlpacaObservatory('alpaca-wk06', observatory_name='wk06')
    alpaca_blocker_wk06 = TreeRequestAlpacaBlocker('alpaca-blocker-wk06', alpaca_wk06)
    blocker_grantor_wk06 = TreeBlockerAccessGrantor('access-grantor-wk06', 'access_grantor', alpaca_blocker_wk06)
    broker_components_wk06 = TreeBaseBrokerDefaultTarget('broker-components-wk06', [blocker_grantor_wk06],
                                                         default_provider=alpaca_blocker_wk06)
    cache_wk06 = TreeCache('cache-wk06', broker_components_wk06)
    conditional_freezer_wk06 = TreeConditionalFreezer('conditional-freezer-wk06', cache_wk06)
    target_provider_wk06 = TreeProvider('target-provider-wk06', 'wk06', conditional_freezer_wk06)

    # --------------------------------------- zb08 ---------------------------------------
    alpaca_zb08 = TreeAlpacaObservatory('alpaca-zb08', observatory_name='zb08')
    alpaca_blocker_zb08 = TreeRequestAlpacaBlocker('alpaca-blocker-zb08', alpaca_zb08)
    blocker_grantor_zb08 = TreeBlockerAccessGrantor('access-grantor-zb08', 'access_grantor', alpaca_blocker_zb08)
    broker_components_zb08 = TreeBaseBrokerDefaultTarget('broker-components-zb08', [blocker_grantor_zb08],
                                                         default_provider=alpaca_blocker_zb08)
    cache_zb08 = TreeCache('cache-zb08', broker_components_zb08)
    conditional_freezer_zb08 = TreeConditionalFreezer('conditional-freezer-zb08', cache_zb08)
    target_provider_zb08 = TreeProvider('target-provider-zb08', 'zb08', conditional_freezer_zb08)

    # --------------------------------------- jk15 ---------------------------------------
    alpaca_jk15 = TreeAlpacaObservatory('alpaca-jk15', observatory_name='jk15')
    alpaca_blocker_jk15 = TreeRequestAlpacaBlocker('alpaca-blocker-jk15', alpaca_jk15)
    blocker_grantor_jk15 = TreeBlockerAccessGrantor('access-grantor-jk15', 'access_grantor', alpaca_blocker_jk15)
    broker_components_jk15 = TreeBaseBrokerDefaultTarget('broker-components-jk15', [blocker_grantor_jk15],
                                                         default_provider=alpaca_blocker_jk15)
    cache_jk15 = TreeCache('cache-jk15', broker_components_jk15)
    conditional_freezer_jk15 = TreeConditionalFreezer('conditional-freezer-jk15', cache_jk15)
    target_provider_jk15 = TreeProvider('target-provider-jk15', 'jk15', conditional_freezer_jk15)

    # --------------------------------------- wg25 ---------------------------------------
    alpaca_wg25 = TreeAlpacaObservatory('alpaca-wg25', observatory_name='wg25')
    alpaca_blocker_wg25 = TreeRequestAlpacaBlocker('alpaca-blocker-wg25', alpaca_wg25)
    blocker_grantor_wg25 = TreeBlockerAccessGrantor('access-grantor-wg25', 'access_grantor', alpaca_blocker_wg25)
    broker_components_wg25 = TreeBaseBrokerDefaultTarget('broker-components-wg25', [blocker_grantor_wg25],
                                                         default_provider=alpaca_blocker_wg25)
    cache_wg25 = TreeCache('cache-wg25', broker_components_wg25)
    conditional_freezer_wg25 = TreeConditionalFreezer('conditional-freezer-wg25', cache_wg25)
    target_provider_wg25 = TreeProvider('target-provider-wg25', 'wg25', conditional_freezer_wg25)

    # --------------------------------------- iris ---------------------------------------
    alpaca_iris = TreeAlpacaObservatory('alpaca-iris', observatory_name='iris')
    alpaca_blocker_iris = TreeRequestAlpacaBlocker('alpaca-blocker-iris', alpaca_iris)
    blocker_grantor_iris = TreeBlockerAccessGrantor('access-grantor-iris', 'access_grantor', alpaca_blocker_iris)
    broker_components_iris = TreeBaseBrokerDefaultTarget('broker-components-iris', [blocker_grantor_iris],
                                                         default_provider=alpaca_blocker_iris)
    cache_iris = TreeCache('cache-iris', broker_components_iris)
    conditional_freezer_iris = TreeConditionalFreezer('conditional-freezer-iris', cache_iris)
    target_provider_iris = TreeProvider('target-provider-iris', 'iris', conditional_freezer_iris)

    # --------------------------------------- sim ---------------------------------------
    alpaca_sim = TreeAlpacaObservatory('alpaca-sim', observatory_name='sim')
    alpaca_blocker_sim = TreeRequestAlpacaBlocker('alpaca-blocker-sim', alpaca_sim)
    blocker_grantor_sim = TreeBlockerAccessGrantor('access-grantor-sim', 'access_grantor', alpaca_blocker_sim)
    broker_components_sim = TreeBaseBrokerDefaultTarget('broker-components-sim', [blocker_grantor_sim],
                                                        default_provider=alpaca_blocker_sim)
    cache_sim = TreeCache('cache-sim', broker_components_sim)
    conditional_freezer_sim = TreeConditionalFreezer('conditional-freezer-sim', cache_sim)
    target_provider_sim = TreeProvider('target-provider-sim', 'sim', conditional_freezer_sim)

    # --------------------------------------- dev ---------------------------------------
    alpaca_dev = TreeAlpacaObservatory('alpaca-dev', observatory_name='dev')
    alpaca_blocker_dev = TreeRequestAlpacaBlocker('alpaca-blocker-dev', alpaca_dev)
    blocker_grantor_dev = TreeBlockerAccessGrantor('access-grantor-dev', 'access_grantor', alpaca_blocker_dev)
    broker_components_dev = TreeBaseBrokerDefaultTarget('broker-components-dev', [blocker_grantor_dev],
                                                        default_provider=alpaca_blocker_dev)
    cache_dev = TreeCache('cache-dev', broker_components_dev)
    conditional_freezer_dev = TreeConditionalFreezer('conditional-freezer-dev', cache_dev)
    target_provider_dev = TreeProvider('target-provider-dev', 'dev', conditional_freezer_dev)

    # -----------------------------gather alpacas components -----------------------------
    broker_front_oca = TreeBaseBroker('broker-front-oca',
                                      [target_provider_wk06,
                                       target_provider_zb08,
                                       target_provider_jk15,
                                       target_provider_wg25,
                                       target_provider_iris,
                                       target_provider_sim,
                                       target_provider_dev])

    # ------------------------------ front receiver blocks -------------------------------
    rs = RequestSolver(data_provider=broker_front_oca)
    vr = Router(request_solver=rs, name="Router-Observatorio-Cerro-Armazones")
    return vr
