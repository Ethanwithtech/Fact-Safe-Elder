import React, { useState, useEffect } from 'react';
import { 
  Card, Tabs, Button, Progress, Table, Tag, Space, Row, Col, 
  Statistic, Alert, Select, Upload, message, Modal, Form, Input, 
  InputNumber, Switch, Timeline, Badge, Descriptions
} from 'antd';
import {
  CloudUploadOutlined, PlayCircleOutlined, PauseCircleOutlined,
  ReloadOutlined, RocketOutlined, DatabaseOutlined, LineChartOutlined,
  ExperimentOutlined, CheckCircleOutlined, CloseCircleOutlined,
  LoadingOutlined, WarningOutlined
} from '@ant-design/icons';
import axios from 'axios';
import './TrainingDashboard.css';

const { Option } = Select;
const { Dragger } = Upload;

interface TrainingTask {
  task_id: string;
  model_type: string;
  dataset_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  progress: number;
  current_epoch: number;
  total_epochs: number;
  best_metric: number;
  created_at: string;
  metrics?: any;
  logs?: string[];
}

interface Dataset {
  id: string;
  name: string;
  description: string;
  type: string;
  size: string;
  created_at: string;
}

interface Model {
  id: string;
  name: string;
  type: string;
  status: string;
  metrics?: {
    accuracy: number;
    f1?: number;
  };
}

const TrainingDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [trainingTasks, setTrainingTasks] = useState<TrainingTask[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedTask, setSelectedTask] = useState<TrainingTask | null>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [showTrainModal, setShowTrainModal] = useState(false);
  const [form] = Form.useForm();

  const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // 每5秒更新一次
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      // 获取数据集列表
      const datasetsRes = await axios.get(`${baseURL}/api/ai/dataset/list`);
      setDatasets(datasetsRes.data.datasets || []);

      // 获取模型列表
      const modelsRes = await axios.get(`${baseURL}/api/ai/models/list`);
      setModels(modelsRes.data.models || []);

      // 获取训练任务（模拟数据）
      setTrainingTasks([
        {
          task_id: 'task_001',
          model_type: 'chatglm',
          dataset_id: 'mcfend_v1',
          status: 'running',
          progress: 65,
          current_epoch: 7,
          total_epochs: 10,
          best_metric: 0.88,
          created_at: '2025-01-27T10:00:00'
        }
      ]);
    } catch (error) {
      console.error('获取数据失败:', error);
    }
  };

  const startTraining = async (values: any) => {
    try {
      setIsTraining(true);
      const response = await axios.post(`${baseURL}/api/ai/train`, values);
      
      if (response.data.success) {
        message.success('训练任务已启动');
        setShowTrainModal(false);
        form.resetFields();
        fetchData();
      }
    } catch (error) {
      message.error('启动训练失败');
    } finally {
      setIsTraining(false);
    }
  };

  const stopTraining = async (taskId: string) => {
    try {
      await axios.post(`${baseURL}/api/ai/train/stop/${taskId}`);
      message.success('训练已停止');
      fetchData();
    } catch (error) {
      message.error('停止训练失败');
    }
  };

  const deployModel = async (modelId: string) => {
    try {
      await axios.post(`${baseURL}/api/ai/models/deploy/${modelId}`);
      message.success('模型部署成功');
      fetchData();
    } catch (error) {
      message.error('模型部署失败');
    }
  };

  // 状态标签渲染
  const renderStatus = (status: string) => {
    const statusConfig: any = {
      'pending': { color: 'default', text: '等待中' },
      'running': { color: 'processing', text: '训练中' },
      'completed': { color: 'success', text: '已完成' },
      'failed': { color: 'error', text: '失败' },
      'stopped': { color: 'warning', text: '已停止' },
      'available': { color: 'green', text: '可用' }
    };

    const config = statusConfig[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 概览标签页
  const OverviewTab = () => (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="模型总数"
              value={models.length}
              prefix={<ExperimentOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="数据集总数"
              value={datasets.length}
              prefix={<DatabaseOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="训练任务"
              value={trainingTasks.length}
              prefix={<LoadingOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="平均准确率"
              value={87.5}
              prefix={<LineChartOutlined />}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
      </Row>

      <Card title="🔥 当前训练任务" style={{ marginTop: 16 }}>
        {trainingTasks
          .filter(task => task.status === 'running')
          .map(task => (
            <div key={task.task_id} className="training-task-card">
              <div className="task-header">
                <Space>
                  <Badge status="processing" />
                  <strong>{task.model_type.toUpperCase()}</strong>
                  <span>数据集: {task.dataset_id}</span>
                </Space>
                <Button 
                  size="small" 
                  danger 
                  onClick={() => stopTraining(task.task_id)}
                >
                  停止
                </Button>
              </div>
              
              <div className="task-progress">
                <div className="progress-info">
                  <span>Epoch {task.current_epoch}/{task.total_epochs}</span>
                  <span>最佳指标: {task.best_metric.toFixed(3)}</span>
                </div>
                <Progress 
                  percent={task.progress} 
                  status="active"
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
              </div>

              {task.logs && task.logs.length > 0 && (
                <div className="task-logs">
                  <div className="log-console">
                    {task.logs.slice(-3).map((log, index) => (
                      <div key={index} className="log-line">
                        <span className="log-time">[{new Date().toLocaleTimeString()}]</span>
                        <span className="log-text">{log}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        
        {trainingTasks.filter(t => t.status === 'running').length === 0 && (
          <Alert 
            message="当前没有运行中的训练任务"
            type="info"
            showIcon
            action={
              <Button 
                type="primary" 
                size="small"
                onClick={() => setShowTrainModal(true)}
              >
                开始训练
              </Button>
            }
          />
        )}
      </Card>

      <Card title="📊 模型性能对比" style={{ marginTop: 16 }}>
        <Table
          dataSource={models}
          rowKey="id"
          columns={[
            {
              title: '模型名称',
              dataIndex: 'name',
              key: 'name',
              render: (text: string) => <strong>{text}</strong>
            },
            {
              title: '类型',
              dataIndex: 'type',
              key: 'type',
              render: (type: string) => (
                <Tag color="blue">{type.toUpperCase()}</Tag>
              )
            },
            {
              title: '准确率',
              dataIndex: ['metrics', 'accuracy'],
              key: 'accuracy',
              render: (val: number) => val ? `${(val * 100).toFixed(1)}%` : '-',
              sorter: (a: any, b: any) => 
                (a.metrics?.accuracy || 0) - (b.metrics?.accuracy || 0)
            },
            {
              title: 'F1分数',
              dataIndex: ['metrics', 'f1'],
              key: 'f1',
              render: (val: number) => val ? val.toFixed(3) : '-'
            },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: renderStatus
            },
            {
              title: '操作',
              key: 'action',
              render: (_: any, record: Model) => (
                <Space>
                  <Button 
                    type="link" 
                    size="small"
                    onClick={() => deployModel(record.id)}
                    disabled={record.status !== 'available'}
                  >
                    部署
                  </Button>
                  <Button type="link" size="small">评估</Button>
                </Space>
              )
            }
          ]}
          pagination={false}
        />
      </Card>
    </div>
  );

  // 数据集标签页
  const DatasetsTab = () => (
    <div>
      <Card 
        title="数据集管理"
        extra={
          <Button 
            type="primary" 
            icon={<CloudUploadOutlined />}
            onClick={() => message.info('数据集上传功能开发中')}
          >
            上传数据集
          </Button>
        }
      >
        <Table
          dataSource={datasets}
          rowKey="id"
          columns={[
            {
              title: '数据集名称',
              dataIndex: 'name',
              key: 'name',
              render: (text: string, record: Dataset) => (
                <div>
                  <strong>{text}</strong>
                  <div style={{ fontSize: 12, color: '#999' }}>
                    {record.description}
                  </div>
                </div>
              )
            },
            {
              title: '类型',
              dataIndex: 'type',
              key: 'type',
              render: (type: string) => {
                const typeColor: any = {
                  'mcfend': 'purple',
                  'weibo': 'orange',
                  'custom': 'blue'
                };
                return <Tag color={typeColor[type] || 'default'}>{type}</Tag>;
              }
            },
            {
              title: '样本数量',
              dataIndex: 'size',
              key: 'size',
              render: (size: string) => (
                <span>{Number(size).toLocaleString()}</span>
              )
            },
            {
              title: '创建时间',
              dataIndex: 'created_at',
              key: 'created_at',
              render: (time: string) => new Date(time).toLocaleDateString()
            },
            {
              title: '操作',
              key: 'action',
              render: (_: any, record: Dataset) => (
                <Space>
                  <Button type="link" size="small">查看</Button>
                  <Button type="link" size="small">预处理</Button>
                  <Button type="link" size="small">增强</Button>
                </Space>
              )
            }
          ]}
        />
      </Card>

      <Card title="数据集统计" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Card size="small" title="数据集分布">
              <div className="dataset-stats">
                <div className="stat-item">
                  <span className="stat-label">MCFEND数据集:</span>
                  <span className="stat-value">23,974 条</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">微博数据集:</span>
                  <span className="stat-value">15,000 条</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">自定义数据集:</span>
                  <span className="stat-value">14,700 条</span>
                </div>
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" title="标签分布">
              <div className="label-distribution">
                <Progress 
                  percent={35} 
                  format={() => '安全'} 
                  strokeColor="#52c41a" 
                />
                <Progress 
                  percent={25} 
                  format={() => '警告'} 
                  strokeColor="#faad14" 
                />
                <Progress 
                  percent={40} 
                  format={() => '危险'} 
                  strokeColor="#ff4d4f" 
                />
              </div>
            </Card>
          </Col>
        </Row>
      </Card>
    </div>
  );

  // 训练历史标签页
  const HistoryTab = () => (
    <Card title="训练历史">
      <Timeline mode="left">
        <Timeline.Item 
          color="green" 
          dot={<CheckCircleOutlined />}
        >
          <div className="timeline-item">
            <div className="timeline-header">
              <strong>ChatGLM模型训练完成</strong>
              <Tag color="success">成功</Tag>
            </div>
            <div className="timeline-meta">
              数据集: MCFEND | 准确率: 92.3% | 耗时: 2小时15分
            </div>
            <div className="timeline-time">2025-01-27 14:30</div>
          </div>
        </Timeline.Item>

        <Timeline.Item 
          color="red"
          dot={<CloseCircleOutlined />}
        >
          <div className="timeline-item">
            <div className="timeline-header">
              <strong>BERT模型训练失败</strong>
              <Tag color="error">失败</Tag>
            </div>
            <div className="timeline-meta">
              错误: GPU内存不足
            </div>
            <div className="timeline-time">2025-01-27 12:15</div>
          </div>
        </Timeline.Item>

        <Timeline.Item 
          color="orange"
          dot={<WarningOutlined />}
        >
          <div className="timeline-item">
            <div className="timeline-header">
              <strong>LLaMA模型训练中断</strong>
              <Tag color="warning">中断</Tag>
            </div>
            <div className="timeline-meta">
              数据集: 微博数据集 | 完成: 6/10 epochs
            </div>
            <div className="timeline-time">2025-01-27 10:45</div>
          </div>
        </Timeline.Item>
      </Timeline>
    </Card>
  );

  const tabItems = [
    { key: 'overview', label: '📊 概览', children: <OverviewTab /> },
    { key: 'datasets', label: '💾 数据集', children: <DatasetsTab /> },
    { key: 'history', label: '📜 训练历史', children: <HistoryTab /> }
  ];

  return (
    <div className="training-dashboard">
      <Alert
        message="🎓 AI模型训练平台"
        description="在这里您可以训练自定义的虚假信息检测模型，管理数据集，并监控训练进度。支持ChatGLM、BERT、LLaMA等多种大模型。"
        type="info"
        showIcon
        closable
        style={{ marginBottom: 16 }}
      />

      <div className="dashboard-actions">
        <Space>
          <Button 
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            onClick={() => setShowTrainModal(true)}
            disabled={isTraining}
          >
            开始新训练
          </Button>
          <Button 
            size="large"
            icon={<ReloadOutlined />}
            onClick={fetchData}
          >
            刷新数据
          </Button>
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />

      {/* 训练配置模态框 */}
      <Modal
        title="🚀 配置新的训练任务"
        open={showTrainModal}
        onCancel={() => setShowTrainModal(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={startTraining}
        >
          <Form.Item
            name="model_type"
            label="选择模型"
            rules={[{ required: true, message: '请选择模型类型' }]}
          >
            <Select size="large" placeholder="选择要训练的模型">
              <Option value="chatglm">ChatGLM-6B (推荐)</Option>
              <Option value="bert">Chinese-BERT</Option>
              <Option value="llama">LLaMA-7B</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="dataset_id"
            label="选择数据集"
            rules={[{ required: true, message: '请选择数据集' }]}
          >
            <Select size="large" placeholder="选择训练数据集">
              <Option value="mcfend_v1">MCFEND多源假新闻数据集</Option>
              <Option value="weibo_rumors">微博谣言数据集</Option>
              <Option value="financial_fraud">金融诈骗数据集</Option>
              <Option value="medical_misinfo">医疗虚假信息数据集</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="epochs"
                label="训练轮数"
                initialValue={10}
              >
                <InputNumber 
                  min={1} 
                  max={100} 
                  style={{ width: '100%' }}
                  size="large"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="batch_size"
                label="批次大小"
                initialValue={8}
              >
                <InputNumber 
                  min={1} 
                  max={64} 
                  style={{ width: '100%' }}
                  size="large"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="learning_rate"
            label="学习率"
            initialValue={0.00005}
          >
            <InputNumber
              min={0.000001}
              max={0.001}
              step={0.000001}
              style={{ width: '100%' }}
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="use_lora"
            label="使用LoRA微调"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="开启" unCheckedChildren="关闭" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit"
                loading={isTraining}
                size="large"
              >
                开始训练
              </Button>
              <Button 
                onClick={() => setShowTrainModal(false)}
                size="large"
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TrainingDashboard;
