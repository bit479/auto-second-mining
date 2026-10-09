Attribute VB_Name = "OreDelineation"
' 3DMine VBA 宏：1004 二次圈矿（在 3DMine 内绘图 + 出报告）
' 数据来源：1004_vba_data.txt（由自动化预处理生成，含炮孔/矿块边界/1m网格/标注/算量）
' 运行：宏菜单 -> 新建工程 -> VBA编辑器 -> 粘贴本模块 -> 运行 OreDelineation
Option Explicit

Sub OreDelineation()
    On Error Resume Next
    Dim drw As Object
    Set drw = ThisDrawing
    If drw Is Nothing Then
        MsgBox "无法获取当前图档", vbExclamation
        Exit Sub
    End If

    Dim F As Integer
    Dim sLine As String
    Dim parts() As String
    Dim i As Long
    Dim benchZ As Double
    benchZ = 3940.63

    F = FreeFile
    Open "D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_vba_data.txt" For Input As #F

    ' 矿块边界暂存：BlockNo -> 点集
    Dim polyNo As Long
    Dim px() As Double, py() As Double, pz As Double
    Dim pcnt As Long
    Dim reportLines As String
    Dim holeCount As Long
    Dim gridCount As Long
    Dim lineCount As Long
    Dim blockCount As Long

    polyNo = 0
    pcnt = 0
    ReDim px(0 To 1000)
    ReDim py(0 To 1000)
    holeCount = 0
    gridCount = 0
    lineCount = 0
    blockCount = 0

    Do While Not EOF(F)
        Line Input #F, sLine
        If Len(sLine) = 0 Then GoTo nextline
        parts = Split(sLine, ",")
        Select Case parts(0)
            Case "BENCH_Z"
                benchZ = CDbl(parts(1))
            Case "HOLE"
                ' 炮孔点（带品位标注文字）
                Dim pt As Object
                Set pt = drw.Library.CreatePoint
                pt.x = CDbl(parts(2))
                pt.y = CDbl(parts(3))
                pt.z = CDbl(parts(4))
                pt.Description = parts(1) & "  " & parts(5)   ' 若 API 不支持则忽略
                pt.Update
                drw.ModelSpace.AddPointEntity pt
                ' 品位小字标注
                Dim lblPt As Object
                Set lblPt = drw.Library.CreatePoint
                lblPt.x = CDbl(parts(2)) + 1.2
                lblPt.y = CDbl(parts(3)) + 1.2
                lblPt.z = CDbl(parts(4))
                Dim stxt As Object
                Set stxt = drw.ModelSpace.AddSText(parts(5), lblPt, 0.8)
                stxt.Update
                holeCount = holeCount + 1
            Case "POLY"
                If polyNo <> CLng(parts(1)) Then
                    ' 结束上一块：画闭合线
                    If pcnt > 2 Then
                        Dim pps As Object
                        Set pps = drw.Library.CreatePoints
                        Dim k As Long
                        For k = 0 To pcnt - 1
                            pps.Add px(k), py(k), pz, 0
                        Next k
                        pps.Add px(0), py(0), pz, 0
                        Dim poly As Object
                        Set poly = drw.ModelSpace.Add3DPoly(pps)
                        poly.Update
                        lineCount = lineCount + 1
                    End If
                    polyNo = CLng(parts(1))
                    pcnt = 0
                End If
                px(pcnt) = CDbl(parts(2))
                py(pcnt) = CDbl(parts(3))
                pz = CDbl(parts(4))
                pcnt = pcnt + 1
            Case "POLYEND"
                If pcnt > 2 Then
                    Dim pps2 As Object
                    Set pps2 = drw.Library.CreatePoints
                    Dim k2 As Long
                    For k2 = 0 To pcnt - 1
                        pps2.Add px(k2), py(k2), pz, 0
                    Next k2
                    pps2.Add px(0), py(0), pz, 0
                    Dim poly2 As Object
                    Set poly2 = drw.ModelSpace.Add3DPoly(pps2)
                    poly2.Update
                    lineCount = lineCount + 1
                End If
                polyNo = 0
                pcnt = 0
            Case "GRID"
                Dim gps As Object
                Set gps = drw.Library.CreatePoints
                gps.Add CDbl(parts(2)), CDbl(parts(3)), benchZ, 0
                gps.Add CDbl(parts(4)), CDbl(parts(5)), benchZ, 0
                Dim gline As Object
                Set gline = drw.ModelSpace.Add3DPoly(gps)
                gline.Update
                gridCount = gridCount + 1
            Case "LABEL"
                Dim lblPt2 As Object
                Set lblPt2 = drw.Library.CreatePoint
                lblPt2.x = CDbl(parts(2))
                lblPt2.y = CDbl(parts(3))
                lblPt2.z = pz
                Dim stxt2 As Object
                Set stxt2 = drw.ModelSpace.AddSText("矿块" & parts(1), lblPt2, 2.5)
                stxt2.Update
            Case "DATA"
                reportLines = reportLines & "矿块" & parts(1) & " | 面积 " & parts(3) _
                    & " m2 | 体积 " & parts(4) & " m3 | 重量 " & parts(5) _
                    & " t | 平均品位 " & parts(6) & " g/t | 金属量 " & parts(7) _
                    & " g | 炮孔 " & parts(8) & " 个" & vbCrLf
                blockCount = blockCount + 1
        End Select
nextline:
    Loop
    Close #F

    drw.Update
    drw.Regen

    ' 报告
    Dim R As Integer
    R = FreeFile
    Open "D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_矿块数据报告.txt" For Output As #R
    Print #R, "BS-3940-1004 二次圈矿数据报告（3DMine VBA 出具）"
    Print #R, ""
    Print #R, reportLines
    Close #R

    MsgBox "完成：炮孔 " & holeCount & " 个，矿块 " & blockCount _
        & " 个，矿界线 " & lineCount & " 条，网格线 " & gridCount & " 条" & vbCrLf & "报告已写入 output\1004_macro\1004_矿块数据报告.txt", vbInformation
End Sub
