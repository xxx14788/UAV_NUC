#ifndef _DYN_A_STAR_H_
#define _DYN_A_STAR_H_

#include <iostream>
#include <ros/ros.h>
#include <ros/console.h>
#include <Eigen/Eigen>
#include <plan_env/grid_map.h>
#include <queue>

constexpr double inf = 1 >> 20;
struct GridNode;
typedef GridNode *GridNodePtr;

struct GridNode
{
	enum enum_state
	{
		OPENSET = 1,
		CLOSEDSET = 2,
		UNDEFINED = 3
	};

	int rounds{0}; // Distinguish every call
	enum enum_state state
	{
		UNDEFINED
	};
	Eigen::Vector3i index;

	double gScore{inf}, fScore{inf};
	GridNodePtr cameFrom{NULL};
};

class NodeComparator
{
public:
	bool operator()(GridNodePtr node1, GridNodePtr node2)
	{
		return node1->fScore > node2->fScore;
	}
};

class AStar
{
private:
	GridMap::Ptr grid_map_;

	inline void coord2gridIndexFast(const double x, const double y, const double z, int &id_x, int &id_y, int &id_z);

	double getDiagHeu(GridNodePtr node1, GridNodePtr node2);
	double getManhHeu(GridNodePtr node1, GridNodePtr node2);
	double getEuclHeu(GridNodePtr node1, GridNodePtr node2);
	inline double getHeu(GridNodePtr node1, GridNodePtr node2);

	bool ConvertToIndexAndAdjustStartEndPoints(const Eigen::Vector3d start_pt, const Eigen::Vector3d end_pt, Eigen::Vector3i &start_idx, Eigen::Vector3i &end_idx);

	inline Eigen::Vector3d Index2Coord(const Eigen::Vector3i &index) const;
	inline bool Coord2Index(const Eigen::Vector3d &pt, Eigen::Vector3i &idx) const;

	//bool (*checkOccupancyPtr)( const Eigen::Vector3d &pos );

	/* 2026-11-11（用户问 5/7 根因，bag 20261111_212822 实测）：
	   撤销"以搜索起点为心、半径=等效膨胀"的自由球。它会把真障碍一起遮住：
	   36.19 s 起点离箱心 0.34 m，箱旁膨胀格在图里已 7 s，球内 0.45 m 全当自由，
	   A* 于是贴箱切角出轨迹，FSM 随即报 Suddenly discovered obstacles。
	   同日深度图实测 <0.30 m 像素数=0（无自机点），证明"起点在膨胀层里"是
	   "离障碍太近"，不是"自己看见自己"。
	   正确语义回上游：起点碰撞由 ConvertToIndexAndAdjustStartEndPoints 沿
	   start->end 反向外推解决。
	   【2026-11-15 二次修正】上面这条"搜索本身必须看膨胀层"已被证伪：A* 只在
	   bspline_optimizer 的碰撞段修补里被调用，用 inflate 会把"膨胀层里但真实可飞"
	   的段尾判死（调用方已按 raw 选点），成批修补失败 -> 旧回环一直不被替换。
	   现硬判据改 raw，膨胀层留给优化器 cost / FSM 规划裕度。 */
	// 2026-11-15（根因修复，最终方向）：A* 的 start/end/搜索统一用 inflate（保住 0.30 安全裕度）。
	// 11-14 的 `end adjust hit cap` 真正原因是**调用方错配**：refineTrajAlgo 的段尾 j 按
	// raw 选（bspline_optimizer.cpp:1264），而被调用的 A* 按 inflate 拒绝。修法是把 j/pj
	// 对齐到 inflate，而不是把 A* 降到 raw —— 11-15 闭环重放实测：硬判据用单点 raw 时，
	// 轨迹从箱顶上方仅 0.10 m 擦过（机体半径 0.17 已被吃掉）。起点仍保留 raw 豁免
	// （飞机物理上可能贴障，见 ConvertToIndexAndAdjustStartEndPoints）。
	inline bool checkOccupancy(const Eigen::Vector3d &pos) {
	  return (bool)grid_map_->getInflateOccupancy(pos);
	}

	// 2026-11-13 v2：原始占据（不含膨胀），用于判断"起点只是落在安全膨胀层"还是真在障碍里
	inline bool checkRawOccupancy(const Eigen::Vector3d &pos) {
	  return grid_map_->getOccupancy(pos) > 0;
	}

	std::vector<GridNodePtr> retrievePath(GridNodePtr current);

	double step_size_, inv_step_size_;
	Eigen::Vector3d center_;
	Eigen::Vector3i CENTER_IDX_, POOL_SIZE_;
	const double tie_breaker_ = 1.0 + 1.0 / 10000;

	std::vector<GridNodePtr> gridPath_;

	GridNodePtr ***GridNodeMap_;
	std::priority_queue<GridNodePtr, std::vector<GridNodePtr>, NodeComparator> openSet_;

	int rounds_{0};

public:
	typedef std::shared_ptr<AStar> Ptr;

	AStar(){};
	~AStar();

	void initGridMap(GridMap::Ptr occ_map, const Eigen::Vector3i pool_size);

	bool AstarSearch(const double step_size, Eigen::Vector3d start_pt, Eigen::Vector3d end_pt);

	std::vector<Eigen::Vector3d> getPath();
};

inline double AStar::getHeu(GridNodePtr node1, GridNodePtr node2)
{
	return tie_breaker_ * getDiagHeu(node1, node2);
}

inline Eigen::Vector3d AStar::Index2Coord(const Eigen::Vector3i &index) const
{
	return ((index - CENTER_IDX_).cast<double>() * step_size_) + center_;
};

inline bool AStar::Coord2Index(const Eigen::Vector3d &pt, Eigen::Vector3i &idx) const
{
	idx = ((pt - center_) * inv_step_size_ + Eigen::Vector3d(0.5, 0.5, 0.5)).cast<int>() + CENTER_IDX_;

	if (idx(0) < 0 || idx(0) >= POOL_SIZE_(0) || idx(1) < 0 || idx(1) >= POOL_SIZE_(1) || idx(2) < 0 || idx(2) >= POOL_SIZE_(2))
	{
		ROS_ERROR("Ran out of pool, index=%d %d %d", idx(0), idx(1), idx(2));
		return false;
	}

	return true;
};

#endif
