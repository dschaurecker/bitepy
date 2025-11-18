////////////////////////////////////////////////////////////////////////
// Copyright (C) 2025 ETH Zurich
// BitePy: A Python Battery Intraday Trading Engine
// Bits to Energy Lab - Chair of Information Management - ETH Zurich
//
// Author: David Schaurecker
//
// Licensed under MIT License, see https://opensource.org/license/mit
///////////////////////////////////////////////////////////////////////

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>          // for automatic conversion of STL containers
// #include <pybind11/numpy.h>        // if you need NumPy arrays
#include <pybind11/chrono.h>       // if you need chrono conversions

#include "Simulation.h"

namespace py = pybind11;

using simParams = SimulationParameters;
using sim = Simulation;

PYBIND11_MODULE(_bitepy, m) {
    m.doc() = "pybind11 wrapper for the Simulation C++ code";
    // Params class
    // **Expose SimulationParameters class**
    py::class_<simParams>(m, "SimulationParameters")
        // Constructor with parameter file path
        // .def(py::init<const std::string&>(), py::arg("paramFilePath"))
        // Constructor with default values
        .def(py::init<>())

        // **Getter and Setter as properties**
        .def_property("storageMax",
                      &simParams::getStorageMaxPy,   // Getter
                      &simParams::setStorageMaxPy)   // Setter
        .def_property("startMonth",
                        &simParams::getStartMonthPy,
                        &simParams::setStartMonthPy)
        .def_property("endMonth",
                        &simParams::getEndMonthPy,
                        &simParams::setEndMonthPy)
        .def_property("startDay",
                        &simParams::getStartDayPy,
                        &simParams::setStartDayPy)
        .def_property("endDay",
                        &simParams::getEndDayPy,
                        &simParams::setEndDayPy)
        .def_property("startHour",
                        &simParams::getStartHourPy,
                        &simParams::setStartHourPy)
        .def_property("endHour",
                        &simParams::getEndHourPy,
                        &simParams::setEndHourPy)
        .def_property("startYear",
                        &simParams::getStartYearPy,
                        &simParams::setStartYearPy)
        .def_property("endYear",
                        &simParams::getEndYearPy,
                        &simParams::setEndYearPy)
        .def_property("startMinute",
                        &simParams::getStartMinutePy,
                        &simParams::setStartMinutePy)
        .def_property("endMinute",
                        &simParams::getEndMinutePy,
                        &simParams::setEndMinutePy)
        .def_property("dpFreq",
                        &simParams::getDpFreqPy,
                        &simParams::setDpFreqPy)
        .def_property("lossIn",
                        &simParams::getLossInPy,
                        &simParams::setLossInPy)
        .def_property("lossOut",
                        &simParams::getLossOutPy,
                        &simParams::setLossOutPy)
        .def_property("linDegCost",
                        &simParams::getLinDegCostPy,
                        &simParams::setLinDegCostPy)
        .def_property("tradingFee",
                        &simParams::getTradingFeePy,
                        &simParams::setTradingFeePy)
        .def_property("withdrawMax",
                        &simParams::getWithdrawMaxPy,
                        &simParams::setWithdrawMaxPy)
        .def_property("injectMax",
                        &simParams::getInjectMaxPy,
                        &simParams::setInjectMaxPy)
        // .def_property("runType",
        //                 &simParams::getRunTypePy,
        //                 &simParams::setRunTypePy)
        // .def_property("tempDir",
        //                 &simParams::getTempDirPy,
        //                 &simParams::setTempDirPy)
        // .def_property("resultsDir",
        //                 &simParams::getResultsDirPy,
        //                 &simParams::setResultsDirPy)
        // .def_property("cmaesParamPath",
        //                 &simParams::getCmaesParamPathPy,
        //                 &simParams::setCmaesParamPathPy)
        .def_property("numStorStates",
                        &simParams::getNumStorStatesPy,
                        &simParams::setNumStorStatesPy)
        // .def_property("stoRoundDec",
        //                 &simParams::getStoRoundDecPy,
        //                 &simParams::setStoRoundDecPy)
        .def_property("pingDelay",
                        &simParams::getPingDelayPy,
                        &simParams::setPingDelayPy)
        .def_property("fixedSolveTime",
                        &simParams::getFixedSolveTimePy,
                        &simParams::setFixedSolveTimePy)
        // .def_property("checkProfit",
        //                 &simParams::getCheckProfitPy,
        //                 &simParams::setCheckProfitPy)
        // .def_property("checkLOExec",
        //                 &simParams::getCheckLOExecPy,
        //                 &simParams::setCheckLOExecPy)
        // .def_property("useSliding",
        //                 &simParams::getUseSlidingPy,
        //                 &simParams::setUseSlidingPy)
        // .def_property("foreHorizonStart",
        //                 &simParams::getForeHorizonStartPy,
        //                 &simParams::setForeHorizonStartPy)
        // .def_property("foreHorizonEnd",
        //                 &simParams::getForeHorizonEndPy,
        //                 &simParams::setForeHorizonEndPy)
        // .def_property("bidAskPenalty",
        //                 &simParams::getBidAskPenaltyPy,
        //                 &simParams::setBidAskPenaltyPy)
        .def_property("minuteDelay",
                    &SimulationParameters::getMinuteDelayPy,
                    &SimulationParameters::setMinuteDelayPy)
        .def_property("logTransactions",
                    &SimulationParameters::getLogTransactionsPy,
                    &SimulationParameters::setLogTransactionsPy)
        .def_property("tradingStartMonth",
                    &SimulationParameters::getTradingStartMonthPy,
                    &SimulationParameters::setTradingStartMonthPy)
        .def_property("tradingStartDay",
                    &SimulationParameters::getTradingStartDayPy,
                    &SimulationParameters::setTradingStartDayPy)
        .def_property("tradingStartYear",
                    &SimulationParameters::getTradingStartYearPy,
                    &SimulationParameters::setTradingStartYearPy)
        .def_property("tradingStartHour",
                    &SimulationParameters::getTradingStartHourPy,
                    &SimulationParameters::setTradingStartHourPy)
        .def_property("tradingStartMinute",
                    &SimulationParameters::getTradingStartMinutePy,
                    &SimulationParameters::setTradingStartMinutePy)
        .def_property("cycleLimit",
                    &SimulationParameters::getCycleLimitPy,
                    &SimulationParameters::setCycleLimitPy)
        .def_property("onlyTraverseLOB",
            &SimulationParameters::getOnlyTraverseLOBPy,
            &SimulationParameters::setOnlyTraverseLOBPy);
        
        // Method to print parameters
        // .def("printParameters", &simParams::printParameters);


    // Expose the Simulation class
    py::class_<sim>(m, "Simulation_cpp")
        // constructor
        // .def(py::init<const std::string &>(),
        //      py::arg("param_path"))
        .def(py::init<>())
        // Expose 'params' as a property
        .def_property("params", 
                      [](sim &self) -> simParams& { return self.params; },  // getter
                      [](sim &self, simParams &new_params) { self.params = new_params; }) // setter
        // method to run
        .def("run",
            &sim::run,
            py::arg("isLastDataset"),
            "Run the simulation. 'isLast' indicates if this is the final run.")

        .def("addOrderQueueFromPandas", &sim::addOrderQueueFromPandas)
        .def("addOrderQueueFromBin", &sim::addOrderQueueFromBin)
        .def("writeOrderBinFromPandas", &sim::writeOrderBinFromPandas)
        .def("writeOrderBinFromCSV", &sim::writeOrderBinFromCSV)

        // Limit order submission functionality
        .def("submitLimitOrdersAndGetMatches", [](Simulation &self, 
                const std::vector<std::string>& transaction_times,
                const std::vector<double>& prices,
                const std::vector<double>& volumes,
                const std::vector<std::string>& sides,
                const std::vector<std::string>& delivery_times) {
            self.submitLimitOrdersAndGetMatches(transaction_times, prices, volumes, sides, delivery_times);
            // Return empty list since this method no longer returns matches directly
            return py::list();
        }, py::arg("transaction_times"), py::arg("prices"), py::arg("volumes"), py::arg("sides"), py::arg("delivery_times"))
        
        .def("getLimitOrderMatches", [](Simulation &self) {
            auto matches = self.getLimitOrderMatches();
            py::list matchList;
            for (const auto &match : matches) {
                py::dict pyMatch;
                pyMatch["submitted_order_id"] = match.submitted_order_id;
                pyMatch["matched_order_id"] = match.matched_order_id;
                pyMatch["match_timestamp"] = match.formatMatchTimestamp();
                pyMatch["delivery_hour"] = match.formatDeliveryHour();
                pyMatch["match_price"] = match.match_price;
                pyMatch["match_volume"] = match.match_volume / 10.;
                pyMatch["submitted_order_side"] = match.submitted_order_side;
                pyMatch["existing_order_side"] = match.existing_order_side;
                matchList.append(pyMatch);
            }
            return matchList;
        })

        .def("clearLimitOrderMatches", &Simulation::clearLimitOrderMatches)

        // Stop time with millisecond precision functionality
        .def("setStopTime", &Simulation::setStopTime, py::arg("stop_time_ms"),
            "Set a stop time in milliseconds since epoch. Simulation will stop once if the last order's submission time is after this stop time.")

        // Check if orders remain in queue
        .def("hasOrdersRemaining", &Simulation::hasOrdersRemaining,
            "Check if there are remaining orders in the order queue")

        // .def("loadForecastMapFromCSV", &Simulation::loadForecastMapFromCSV)
        // .def("loadForecastMapFromPandas", &Simulation::loadForecastMapFromPandas)

        // .def("loadParamMapFromCSV", &Simulation::loadParamMapFromCSV)

        // method to get results
        .def("printSimFinishStats", &sim::printSimFinishStats)

        // returnReward as double
        .def("returnReward", [](sim &self) {
            return self.returnReward();
        })

        // Get limit order book state (using simulation's current time)
        .def("getLimitOrderBookState", [](Simulation &self, double maxAction) {
            auto lobState = self.getLimitOrderBookState(maxAction);
            py::dict result;
            
            for (const auto& deliveryPair : lobState) {
                int64_t deliveryTime = deliveryPair.first;
                const auto& dataMap = deliveryPair.second;
                
                py::dict productData;
                // Sell order attributes
                productData["sell_ids"] = dataMap.at("sell_ids");
                productData["sell_initial_ids"] = dataMap.at("sell_initial_ids");
                productData["sell_starts"] = dataMap.at("sell_starts");
                productData["sell_cancels"] = dataMap.at("sell_cancels");
                productData["sell_prices"] = dataMap.at("sell_prices");
                productData["sell_volumes"] = dataMap.at("sell_volumes");
                productData["sell_forecasts"] = dataMap.at("sell_forecasts");
                
                // Buy order attributes
                productData["buy_ids"] = dataMap.at("buy_ids");
                productData["buy_initial_ids"] = dataMap.at("buy_initial_ids");
                productData["buy_starts"] = dataMap.at("buy_starts");
                productData["buy_cancels"] = dataMap.at("buy_cancels");
                productData["buy_prices"] = dataMap.at("buy_prices");
                productData["buy_volumes"] = dataMap.at("buy_volumes");
                productData["buy_forecasts"] = dataMap.at("buy_forecasts");
                
                result[py::int_(deliveryTime)] = productData;
            }
            
            return result;
        }, py::arg("max_action"),
        "Get the current state of all limit order books with all order attributes")


        .def("getLogs", [](sim &self) {
            // C++ -> Python
            auto decRecord = self.getDecisionData();
            py::list decisionRec;
            for (const auto &record : decRecord) {
                // Create a Python dictionary to store the record
                py::dict pyRecord;
                pyRecord["hour"] = Simulation::formatDateTime(record.hour);
                pyRecord["storage"] = record.storage;
                pyRecord["position"] = record.position;
                // pyRecord["final_reward"] = record.finalReward;
                pyRecord["full_reward"] = record.fullReward;
                pyRecord["id_reward_no_deg"] = record.idRewardNoDeg;
                pyRecord["cycles"] = record.cycles;
                // Append the record to the results list
                decisionRec.append(pyRecord);
            }

            auto priceRecord = self.getPriceData();
            py::list priceRec;
            for (const auto &record : priceRecord) {
                // Create a Python dictionary to store the record
                py::dict pyRecord;
                pyRecord["hour"] = Simulation::formatDateTime(record.hour);
                pyRecord["low"] = record.low;
                pyRecord["high"] = record.high;
                pyRecord["last"] = record.last;
                pyRecord["wavg"] = record.wavg;
                pyRecord["id3"] = record.id3;
                pyRecord["id1"] = record.id1;
                pyRecord["volume"] = record.volume;
                priceRec.append(pyRecord);
            }

            py::list accOrderList;
            for (const auto &record : self.getAccOrders()) {
                // Create a Python dictionary to store the record
                py::dict pyRecord;

                pyRecord["dp_run"] = record._dpRun;
                pyRecord["time"] = LogAcceptedOrder::epochToLocalDateTimeMS(record.time);
                pyRecord["id"] = record.id;
                pyRecord["initial_id"] = record.initialId;
                pyRecord["start"] = LogAcceptedOrder::epochToLocalDateTimeMS(record.start);
                pyRecord["cancel"] = LogAcceptedOrder::epochToLocalDateTimeMS(record.cancel);
                pyRecord["delivery"] = LogAcceptedOrder::epochToLocalDateTime(record.delivery);
                pyRecord["type"] = record.type == LimitOrder::Type::Buy ? "Buy" : "Sell";
                pyRecord["price"] = record.price / 100.0;
                pyRecord["volume"] = record.volume / 10.0;
                pyRecord["partial"] = record.partial;
                pyRecord["partial_volume"] = record.partialVolume / 10.0;
                accOrderList.append(pyRecord);
            }

            py::list execOrderList;
            for (const auto &record : self.getExOrders()) {
                // Create a Python dictionary to store the record
                py::dict pyRecord;

                pyRecord["dp_run"] = record.dpRun;
                pyRecord["time"] = ExecMarketOrder::epochToDateTimeMS(record.time);
                pyRecord["last_solve_time"] = ExecMarketOrder::epochToDateTimeMS(record.lastSolveTime);
                pyRecord["hour"] = ExecMarketOrder::epochToDateTime(record.hour);
                pyRecord["reward"] = record.reward / 1000.0;
                pyRecord["reward_incl_deg_costs"] = record.rewardInclDegCosts / 1000.0;
                pyRecord["volume"] = record.volume / 10.0;
                pyRecord["type"] = record.type == LimitOrder::Type::Buy ? "Buy" : "Sell";
                pyRecord["final_pos"] = record.finalPos / 10.0;
                pyRecord["final_stor"] = record.finalStor / 10.0;
                // pyRecord["prae_final_pos"] = record.praeFinalPos / 10.0;
                // pyRecord["prae_final_stor"] = record.praeFinalStor / 10.0;
                // pyRecord["prae_init_storage"] = record.praeInitStorage / 10.0;
                execOrderList.append(pyRecord);
            }

            py::list foreOrderList;
            for (const auto &record : self.getForeOrders()) {
                // Create a Python dictionary to store the record
                py::dict pyRecord;

                pyRecord["dp_run"] = record.dpRun;
                pyRecord["time"] = ForeLogOrder::epochToDateTimeMS(record.time);
                pyRecord["last_solve_time"] = ForeLogOrder::epochToDateTimeMS(record.lastSolveTime);
                pyRecord["hour"] = ForeLogOrder::epochToDateTime(record.hour);
                pyRecord["cancel"] = ForeLogOrder::epochToDateTimeMS(record.cancel);
                pyRecord["type"] = record.type == LimitOrder::Type::Buy ? "Buy" : "Sell";
                pyRecord["price"] = record.price / 100.0;
                pyRecord["volume"] = record.volume / 10.0;
                foreOrderList.append(pyRecord);
            }

            py::list removedOrdersList;
            for (const auto &record : self.getRemOrders()) {
                // Create a Python dictionary to store the record
                py::dict pyRecord;

                pyRecord["dp_run"] = record.dpRun;
                pyRecord["time"] = ExecMarketOrder::epochToDateTimeMS(record.time);
                pyRecord["last_solve_time"] = ExecMarketOrder::epochToDateTimeMS(record.lastSolveTime);
                pyRecord["hour"] = ExecMarketOrder::epochToDateTime(record.hour);
                pyRecord["reward"] = record.reward / 1000.0;
                pyRecord["reward_incl_deg_costs"] = record.rewardInclDegCosts / 1000.0;
                pyRecord["volume"] = record.volume / 10.0;
                pyRecord["type"] = record.type == LimitOrder::Type::Buy ? "Buy" : "Sell";
                pyRecord["final_pos"] = record.finalPos / 10.0;
                pyRecord["final_stor"] = record.finalStor / 10.0;
                // pyRecord["prae_final_pos"] = record.praeFinalPos / 10.0;
                // pyRecord["prae_final_stor"] = record.praeFinalStor / 10.0;
                // pyRecord["prae_init_storage"] = record.praeInitStorage / 10.0;
                removedOrdersList.append(pyRecord);
            }

            py::list balOrderList;
            for (const auto &record : self.getBalOrders()) {
                // Create a Python dictionary to store the record
                py::dict pyRecord;

                pyRecord["dp_run"] = record.dpRun;
                pyRecord["time"] = BalancingOrder::epochToDateTimeMS(record.time);
                pyRecord["hour"] = BalancingOrder::epochToDateTime(record.hour);
                pyRecord["volume"] = record.volume / 10.0;
                balOrderList.append(pyRecord);
            }
            // Return the results to Python
            return py::make_tuple(decisionRec, priceRec, accOrderList, execOrderList, foreOrderList, removedOrdersList, balOrderList);
        })

        .def("getTransactions", [](Simulation &self) {
            // Get transaction records and return them to Python
            py::list transactionList;
            for (const auto &record : self.getAndClearTransactions()) {
                py::dict pyRecord;
                pyRecord["timestamp"] = record.formatTimestamp();
                pyRecord["delivery_hour"] = record.formatDeliveryHour();
                pyRecord["price"] = record.price;
                pyRecord["volume"] = record.volume / 10.0; // Convert from internal units to MW
                pyRecord["buy_order_type"] = record.buy_order_type;
                pyRecord["sell_order_type"] = record.sell_order_type;
                pyRecord["buy_order_id"] = record.buy_order_id;
                pyRecord["sell_order_id"] = record.sell_order_id;
                transactionList.append(pyRecord);
            }
            return transactionList;
        })

        .def("return_vol_price_pairs", [](sim &self, const bool last, const int frequency, const std::vector<int>& volumes) {
            py::list vol_price_list;
            std::map<int64_t, std::map<int64_t, std::map<int, std::pair<int,int>>>> priceVolMap = self.return_vol_price_pairs(last, frequency, volumes);
            
            for (const auto& [currTime, innerMap] : priceVolMap) {
                for (const auto& [delHour, innerMap2] : innerMap) {
                    for (const auto& [volume, price] : innerMap2) {
                        py::dict pyRecord;
                        pyRecord["current_time"] = ExecMarketOrder::epochToDateTimeMS(currTime);
                        pyRecord["delivery_hour"] = ExecMarketOrder::epochToDateTime(delHour);
                        pyRecord["volume"] = volume / 10.0;
                        pyRecord["price_full"] = price.first / 1000.0;
                        pyRecord["worst_accepted_price"] = price.second / 100.0;
                        vol_price_list.append(pyRecord);
                    }
                }
            }

            return vol_price_list;
        }, py::arg("last"), py::arg("frequency"), py::arg("volumes"),
        "Returns a list of dictionaries with volume and price pairs.")
        
        // Solve the dynamic programming problem using the last placed order's time
        .def("solve", [](Simulation &self) {
            auto orders = self.solve();
            py::list orderList;
            for (const auto &order : orders) {
                py::dict pyOrder;
                pyOrder["dp_run"] = order.dpRun;
                pyOrder["time"] = ExecMarketOrder::epochToDateTimeMS(order.time);
                pyOrder["last_solve_time"] = ExecMarketOrder::epochToDateTimeMS(order.lastSolveTime);
                pyOrder["hour"] = ExecMarketOrder::epochToDateTime(order.hour);
                pyOrder["reward"] = order.reward / 1000.0;
                pyOrder["reward_incl_deg_costs"] = order.rewardInclDegCosts / 1000.0;
                pyOrder["volume"] = order.volume / 10.0;
                pyOrder["type"] = order.type == LimitOrder::Type::Buy ? "Buy" : "Sell";
                pyOrder["final_pos"] = order.finalPos / 10.0;
                pyOrder["final_stor"] = order.finalStor / 10.0;
                orderList.append(pyOrder);
            }
            return orderList;
        }, "Solve the dynamic programming problem once using the time of the last placed order. Returns a list of executed market orders.");
}