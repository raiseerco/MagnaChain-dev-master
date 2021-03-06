// Copyright (c) 2016-2019 The MagnaChain Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.
#ifndef CONTRACT_DB_H
#define CONTRACT_DB_H

#include "transaction/txdb.h"
#include <boost/threadpool.hpp>

// 合约某高度存盘数据项
class ContractDataSave
{
public:
    uint256 blockHash;
    boost::optional<std::string> data;

    ADD_SERIALIZE_METHODS;
    template <typename Stream, typename Operation>
    inline void SerializationOp(Stream& s, Operation ser_action)
    {
        READWRITE(blockHash);
        READWRITE(data);
    }
};

// 合约某高度存盘数据
class DBContractInfoByHeight
{
public:
    bool dirty = false;
    int32_t blockHeight;
    std::vector<uint256> vecBlockHash;
    std::vector<std::string> vecBlockContractData;

    ADD_SERIALIZE_METHODS;
    template <typename Stream, typename Operation>
    inline void SerializationOp(Stream& s, Operation ser_action) {
        READWRITE(blockHeight);
    }
};

// 区块关联的智能合约存盘数据
class DBContractInfo
{
public:
    std::string code;
    std::list<DBContractInfoByHeight> items;

    ADD_SERIALIZE_METHODS;
    template <typename Stream, typename Operation>
    inline void SerializationOp(Stream& s, Operation ser_action) {
        READWRITE(code);
        READWRITE(items);
    }
};

class MCContractID;
typedef std::map<MCContractID, ContractInfo> CONTRACT_DATA;

struct ContractTxFinalData
{
public:
    std::map<MCContractID, MCAmount> contractCoins;
    CONTRACT_DATA data;
};

class ContractContext
{
    friend class ContractDataDB;

public:
    CONTRACT_DATA cache;    // 数据缓存，用于回滚
    CONTRACT_DATA data;
    CONTRACT_DATA prevData;
    std::vector<ContractTxFinalData> txFinalData;

public:
    void SetCache(const MCContractID& contractId, ContractInfo& contractInfo);
    void SetData(const MCContractID& contractId, ContractInfo& contractInfo);
    bool GetData(const MCContractID& contractId, ContractInfo& contractInfo);
    void Commit();
    void ClearCache();
    void ClearData();
    void ClearAll();
};

class SmartLuaState;
class MagnaChainAddress;

struct SmartContractThreadData
{
    int offset;
    uint16_t groupSize;
    int blockHeight;
    std::vector<MCAmount> coins;
    ContractContext contractContext;
    MCBlockIndex* pPrevBlockIndex;
    CoinAmountCache* pCoinAmountCache;
    std::set<uint256> associationTransactions;
};

typedef std::map<uint256, std::vector<std::map<MCContractID, ContractInfo>>> BLOCK_CONTRACT_DATA;
class ContractDataDB
{
private:
    std::atomic<bool> interrupt;
    MCDBWrapper db;
    MCDBBatch writeBatch;
    MCDBBatch removeBatch;
    std::vector<uint160> removes;
    boost::threadpool::pool threadPool;
    std::map<boost::thread::id, SmartLuaState*> threadId2SmartLuaState;
    mutable MCCriticalSection cs_cache;

    // 合约缓存，同时包含多个合约对应的多个块合约数据快照
    std::map<MCContractID, DBContractInfo> contractData;
    BLOCK_CONTRACT_DATA blockContractData;
    std::map<int, std::vector<std::pair<uint256, bool>>> mapHeightHash;

public:
    ContractContext contractContext;

public:
    ContractDataDB() = delete;
    ContractDataDB(const ContractDataDB&) = delete;
    ContractDataDB& operator=(const ContractDataDB&) = delete;
    ContractDataDB(const fs::path& path, size_t nCacheSize, bool fMemory, bool fWipe);
    static void InitializeThread(ContractDataDB* contractDB);

    int GetContractInfo(const MCContractID& contractId, ContractInfo& contractInfo, MCBlockIndex* currentPrevBlockIndex);

    bool RunBlockContract(MCBlock* pBlock, ContractContext* pContractContext, CoinAmountCache* pCoinAmountCache);
    void ExecutiveTransactionContract(MCBlock* pBlock, SmartContractThreadData* threadData);

    bool WriteBatch(MCDBBatch& batch);
    bool WriteBlockContractInfoToDisk(MCBlockIndex* pBlockIndex, ContractContext* contractContext);
    bool UpdateBlockContractToDisk(MCBlockIndex* pBlockIndex);
    void PruneContractInfo();
};
extern ContractDataDB* mpContractDb;

extern MCAmount GetTxContractOut(const MCTransaction& tx);

#endif
