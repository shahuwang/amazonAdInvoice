#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 Temu 各区账务明细 Excel，汇总 SKU 维度的回款、退款、赔付数据。

用法:
    python3 parse_temu_fund.py -folder ./temu
"""

import argparse
import sys
import pandas as pd
from pathlib import Path

REQUIRED_FILES = {
    "欧区": "欧区账务明细.xlsx",
    "美区": "美区账务明细.xlsx",
    "全球区": "全球区账务明细.xlsx",
}


def format_excel_worksheet(ws):
    for col in ws.iter_cols(min_row=1, max_row=1):
        header = col[0].value
        if not header:
            continue
        for cell in ws[col[0].column_letter]:
            if cell.row == 1:
                continue
            if isinstance(cell.value, (int, float)):
                if "率" in str(header) or "比例" in str(header):
                    cell.number_format = "0.00%"
                else:
                    cell.number_format = "0.00"


def process_file(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    with pd.ExcelFile(str(input_path)) as xl:
        # 1. 读取交易结算
        df_settle = pd.read_excel(xl, sheet_name="交易结算")
        df_settle["金额"] = pd.to_numeric(df_settle["金额"], errors="coerce").fillna(0)
        for col in ["SKU ID", "SKU货号", "货品名称", "SKU属性"]:
            if col in df_settle.columns:
                df_settle[col] = df_settle[col].astype(str).str.strip()

        # 2. 读取消费者履约保障表
        comp_sheet_keywords = ["消费者履约保障", "消费者及履约保障"]
        comp_sheets = [
            s for s in xl.sheet_names if any(kw in s for kw in comp_sheet_keywords)
        ]
        comp_dfs = []
        comp_sku_sheets = {}
        for sheet in comp_sheets:
            df_comp = pd.read_excel(xl, sheet_name=sheet)
            if "赔付金额" not in df_comp.columns:
                continue
            df_comp["赔付金额"] = pd.to_numeric(
                df_comp["赔付金额"], errors="coerce"
            ).fillna(0)
            for col in ["SKU ID", "SKU货号"]:
                if col in df_comp.columns:
                    df_comp[col] = df_comp[col].astype(str).str.strip()
            comp_cols = ["SKU ID", "SKU货号", "赔付金额"]
            info_cols = [
                c
                for c in ["SKU ID", "SKU货号", "货品名称", "SKU属性"]
                if c in df_comp.columns
            ]
            comp_dfs.append(df_comp[comp_cols])
            comp_sku_sheets[sheet] = (
                df_comp.groupby(["SKU ID", "SKU货号"])["赔付金额"].sum().reset_index()
            )
            if info_cols:
                comp_sku_sheets[sheet + "_info"] = df_comp[info_cols].drop_duplicates(
                    subset=["SKU ID", "SKU货号"]
                )

        # 3. SKU回款汇总
        pivot = (
            df_settle.groupby(["SKU ID", "SKU货号", "货品名称", "SKU属性", "交易类型"])[
                "金额"
            ]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )

        # 收集赔付表中的 SKU 基础信息
        comp_info_parts = []
        for sheet_name in comp_sheets:
            info_key = sheet_name + "_info"
            if info_key in comp_sku_sheets:
                comp_info_parts.append(comp_sku_sheets[info_key])
        if comp_info_parts:
            comp_info = pd.concat(comp_info_parts, ignore_index=True).drop_duplicates(
                subset=["SKU ID", "SKU货号"]
            )
        else:
            comp_info = None

        sheet_col_map = {}
        for sheet_name in comp_sheets:
            if sheet_name not in comp_sku_sheets:
                continue
            df_comp_sheet = comp_sku_sheets[sheet_name]
            if "售后补寄" in sheet_name:
                short_name = "售后补寄赔付金额"
            elif "售后问题" in sheet_name:
                short_name = "售后问题赔付金额"
            else:
                short_name = f"赔付金额-{sheet_name}"
            sheet_col_map[sheet_name] = short_name
            df_comp_sheet = df_comp_sheet.rename(columns={"赔付金额": short_name})
            pivot = pivot.merge(df_comp_sheet, on=["SKU ID", "SKU货号"], how="outer")
            pivot[short_name] = pivot[short_name].fillna(0)

        if comp_dfs:
            df_comp_all = pd.concat(comp_dfs, ignore_index=True)
            comp_total = (
                df_comp_all.groupby(["SKU ID", "SKU货号"])["赔付金额"]
                .sum()
                .reset_index()
            )
            comp_total = comp_total.rename(columns={"赔付金额": "总赔付金额"})
        else:
            comp_total = pd.DataFrame(columns=["SKU ID", "SKU货号", "总赔付金额"])

        pivot = pivot.merge(comp_total, on=["SKU ID", "SKU货号"], how="outer")
        pivot["总赔付金额"] = pivot["总赔付金额"].fillna(0)

        # 补充 outer join 带来的缺失文本信息
        if comp_info is not None:
            pivot = pivot.merge(
                comp_info, on=["SKU ID", "SKU货号"], how="left", suffixes=("", "_comp")
            )
            for col in ["货品名称", "SKU属性"]:
                comp_col = f"{col}_comp"
                if comp_col in pivot.columns:
                    pivot[col] = pivot[col].fillna(pivot[comp_col])
                    pivot = pivot.drop(columns=[comp_col])

        static_cols = ["SKU ID", "SKU货号", "货品名称", "SKU属性"]
        known_cols = list(sheet_col_map.values()) + [
            "总赔付金额",
            "净回款总额",
        ]
        tx_cols = [
            c for c in pivot.columns if c not in static_cols and c not in known_cols
        ]
        for col in tx_cols:
            pivot[col] = pivot[col].fillna(0)
        pivot["货品名称"] = pivot["货品名称"].fillna("")
        pivot["SKU属性"] = pivot["SKU属性"].fillna("")
        pivot["净回款总额"] = pivot[tx_cols].sum(axis=1) - pivot["总赔付金额"]

        for col in list(sheet_col_map.values()) + ["总赔付金额"]:
            if col in pivot.columns:
                pivot[col] = -pivot[col]

        front_cols = static_cols
        comp_ordered = []
        for sheet in comp_sheets:
            if sheet in sheet_col_map:
                comp_ordered.append(sheet_col_map[sheet])
        back_cols = comp_ordered + ["总赔付金额", "净回款总额"]
        mid_cols = [c for c in pivot.columns if c not in front_cols + back_cols]
        pivot = pivot[front_cols + mid_cols + back_cols]

        # 4. SKU指标分析
        settle_grp = df_settle.groupby(["SKU ID", "SKU货号", "货品名称", "SKU属性"])

        metrics_rows = []
        seen_skus = set()
        for (sku_id, sku_no, goods_name, sku_attr), g in settle_grp:
            seen_skus.add((sku_id, sku_no))
            回款_mask = g["交易类型"].isin(["销售回款", "非商责补贴"])
            退款_mask = g["交易类型"] == "销售冲回"

            回款订单数量 = int(回款_mask.sum())
            退款订单数量 = int(退款_mask.sum())
            回款总额_val = float(g.loc[回款_mask, "金额"].sum())
            销售回款_val = float(g[g["交易类型"] == "销售回款"]["金额"].sum())
            退货总额_val = abs(float(g.loc[退款_mask, "金额"].sum()))

            退货率 = 退款订单数量 / 回款订单数量 if 回款订单数量 > 0 else 0.0
            退货金额比例 = 退货总额_val / 销售回款_val if 销售回款_val > 0 else 0.0

            if comp_dfs:
                df_comp_all_local = pd.concat(comp_dfs, ignore_index=True)
                comp_sub = df_comp_all_local[
                    (df_comp_all_local["SKU ID"] == sku_id)
                    & (df_comp_all_local["SKU货号"] == sku_no)
                ]
                赔付金额_val = float(comp_sub["赔付金额"].sum())
                赔付订单数量 = int(len(comp_sub))
            else:
                赔付金额_val = 0.0
                赔付订单数量 = 0

            赔付率 = 赔付订单数量 / 回款订单数量 if 回款订单数量 > 0 else 0.0
            赔付金额比例 = 赔付金额_val / 回款总额_val if 回款总额_val > 0 else 0.0

            metrics_rows.append(
                {
                    "SKU ID": sku_id,
                    "SKU货号": sku_no,
                    "货品名称": goods_name,
                    "SKU属性": sku_attr,
                    "回款订单数量": 回款订单数量,
                    "退款订单数量": 退款订单数量,
                    "退货率": 退货率,
                    "赔付订单数量": 赔付订单数量,
                    "赔付率": 赔付率,
                    "退货总额": round(退货总额_val, 2),
                    "退货金额比例": 退货金额比例,
                    "赔付金额": round(赔付金额_val, 2),
                    "赔付金额比例": 赔付金额比例,
                }
            )

        # 补充只有赔付记录、没有交易结算记录的 SKU
        if comp_dfs:
            df_comp_all_local = pd.concat(comp_dfs, ignore_index=True)
            extra_skus = df_comp_all_local[
                ~df_comp_all_local.set_index(["SKU ID", "SKU货号"]).index.isin(
                    seen_skus
                )
            ][["SKU ID", "SKU货号"]].drop_duplicates()
            for _, row in extra_skus.iterrows():
                sku_id, sku_no = row["SKU ID"], row["SKU货号"]
                comp_sub = df_comp_all_local[
                    (df_comp_all_local["SKU ID"] == sku_id)
                    & (df_comp_all_local["SKU货号"] == sku_no)
                ]
                赔付金额_val = float(comp_sub["赔付金额"].sum())
                赔付订单数量 = int(len(comp_sub))
                # 尝试从赔付表中补全货品名称和 SKU属性
                goods_name = ""
                sku_attr = ""
                if "货品名称" in comp_sub.columns:
                    goods_name = (
                        str(comp_sub["货品名称"].iloc[0]) if len(comp_sub) > 0 else ""
                    )
                if "SKU属性" in comp_sub.columns:
                    sku_attr = (
                        str(comp_sub["SKU属性"].iloc[0]) if len(comp_sub) > 0 else ""
                    )
                metrics_rows.append(
                    {
                        "SKU ID": sku_id,
                        "SKU货号": sku_no,
                        "货品名称": goods_name,
                        "SKU属性": sku_attr,
                        "回款订单数量": 0,
                        "退款订单数量": 0,
                        "退货率": 0.0,
                        "赔付订单数量": 赔付订单数量,
                        "赔付率": 0.0,
                        "退货总额": 0.0,
                        "退货金额比例": 0.0,
                        "赔付金额": round(赔付金额_val, 2),
                        "赔付金额比例": 0.0,
                    }
                )

        df_metrics = pd.DataFrame(metrics_rows)

    return pivot, df_metrics


def write_region_excel(pivot: pd.DataFrame, metrics: pd.DataFrame, output_path: Path):
    with pd.ExcelWriter(str(output_path), engine="openpyxl") as writer:
        pivot.to_excel(writer, index=False, sheet_name="SKU回款汇总")
        metrics.to_excel(writer, index=False, sheet_name="SKU指标分析")
        format_excel_worksheet(writer.sheets["SKU回款汇总"])
        format_excel_worksheet(writer.sheets["SKU指标分析"])
    print(f"已生成: {output_path}")


def merge_region_data(
    pivot_list: list[pd.DataFrame], metrics_list: list[pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # ---- SKU回款汇总合并 ----
    all_pivot = pd.concat(pivot_list, ignore_index=True)
    group_keys = ["SKU ID", "SKU货号", "货品名称", "SKU属性"]
    merged_pivot = all_pivot.groupby(group_keys, as_index=False).sum(numeric_only=False)
    # 重新排列列顺序
    front_cols = group_keys
    back_parts = [
        "售后补寄赔付金额",
        "售后问题赔付金额",
        "总赔付金额",
        "净回款总额",
    ]
    back_cols = [c for c in back_parts if c in merged_pivot.columns]
    mid_cols = [c for c in merged_pivot.columns if c not in front_cols + back_cols]
    merged_pivot = merged_pivot[front_cols + mid_cols + back_cols]

    # ---- SKU指标分析合并 ----
    all_metrics = pd.concat(metrics_list, ignore_index=True)
    sum_metrics = all_metrics.groupby(group_keys, as_index=False).sum(
        numeric_only=False
    )
    # 重新计算比率字段（需要从 merged_pivot 拿交易数据做分母）
    static_keys_set = set(group_keys)
    back_keys_set = set(back_cols)
    tx_cols_merged = [
        c
        for c in merged_pivot.columns
        if c not in static_keys_set and c not in back_keys_set
    ]
    tmp_df = merged_pivot[group_keys].copy()
    tmp_df["_tmp_total"] = merged_pivot[tx_cols_merged].sum(axis=1)
    if "销售回款" in merged_pivot.columns:
        tmp_df["_tmp_sales"] = merged_pivot["销售回款"]
    else:
        tmp_df["_tmp_sales"] = 0.0

    sum_metrics = sum_metrics.merge(tmp_df, on=group_keys, how="left")

    sum_metrics["退货率"] = sum_metrics.apply(
        lambda r: (
            r["退款订单数量"] / r["回款订单数量"] if r["回款订单数量"] > 0 else 0.0
        ),
        axis=1,
    )
    sum_metrics["退货金额比例"] = sum_metrics.apply(
        lambda r: r["退货总额"] / r["_tmp_sales"] if r["_tmp_sales"] > 0 else 0.0,
        axis=1,
    )
    sum_metrics["赔付率"] = sum_metrics.apply(
        lambda r: (
            r["赔付订单数量"] / r["回款订单数量"] if r["回款订单数量"] > 0 else 0.0
        ),
        axis=1,
    )
    sum_metrics["赔付金额比例"] = sum_metrics.apply(
        lambda r: r["赔付金额"] / r["_tmp_total"] if r["_tmp_total"] > 0 else 0.0,
        axis=1,
    )

    sum_metrics = sum_metrics.drop(columns=["_tmp_total", "_tmp_sales"])

    return merged_pivot, sum_metrics


def main():
    parser = argparse.ArgumentParser(description="解析 Temu 各区账务明细")
    parser.add_argument(
        "-folder", "--folder", required=True, help="包含三个区账务明细的文件夹"
    )
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"[ERROR] 指定路径不是文件夹: {folder}")
        sys.exit(1)

    missing = []
    for region, filename in REQUIRED_FILES.items():
        if not (folder / filename).exists():
            missing.append(filename)

    if missing:
        print("[ERROR] 文件夹中缺少以下必需的表格文件:")
        for f in missing:
            print(f"    - {f}")
        print(
            "请确保提供以下三张表格，并按此命名:欧区账务明细.xlsx、美区账务明细.xlsx、全球区账务明细.xlsx"
        )
        sys.exit(1)

    out_dir = folder / "汇总输出"
    out_dir.mkdir(exist_ok=True)

    pivot_list = []
    metrics_list = []
    for region, filename in REQUIRED_FILES.items():
        input_file = folder / filename
        print(f"[INFO] 正在处理 {region} 数据: {filename}")
        pivot, metrics = process_file(input_file)

        output_file = out_dir / f"{region}汇总.xlsx"
        write_region_excel(pivot, metrics, output_file)

        pivot_list.append(pivot)
        metrics_list.append(metrics)

    print("[INFO] 正在生成 店铺汇总.xlsx ...")
    shop_pivot, shop_metrics = merge_region_data(pivot_list, metrics_list)
    shop_output = out_dir / "店铺汇总.xlsx"

    # 构建订单收入汇总表
    income_rows = []
    for region, pivot_df in zip(REQUIRED_FILES.keys(), pivot_list):
        income_rows.append(
            {
                "region": region,
                "赔付总额": pivot_df["总赔付金额"].sum(),
                "净回款总额": pivot_df["净回款总额"].sum(),
            }
        )

    order_income_data = {
        "净回款总额合计": [sum(r["净回款总额"] for r in income_rows)],
        "赔付总额合计": [sum(r["赔付总额"] for r in income_rows)],
    }
    for r in income_rows:
        order_income_data[f"{r['region']}净回款额"] = [r["净回款总额"]]
        order_income_data[f"{r['region']}赔付总额"] = [r["赔付总额"]]

    col_order = (
        ["净回款总额合计"]
        + [f"{r['region']}净回款额" for r in income_rows]
        + ["赔付总额合计"]
        + [f"{r['region']}赔付总额" for r in income_rows]
    )
    df_order_income = pd.DataFrame(order_income_data)[col_order]

    with pd.ExcelWriter(str(shop_output), engine="openpyxl") as writer:
        shop_pivot.to_excel(writer, index=False, sheet_name="SKU回款汇总")
        shop_metrics.to_excel(writer, index=False, sheet_name="SKU指标分析")
        df_order_income.to_excel(writer, index=False, sheet_name="订单收入汇总")
        format_excel_worksheet(writer.sheets["SKU回款汇总"])
        format_excel_worksheet(writer.sheets["SKU指标分析"])
        format_excel_worksheet(writer.sheets["订单收入汇总"])

    print(f"已生成: {shop_output}")
    print(f"\n全部处理完成，输出目录: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
