"""
Advanced Scientific Visualizations for SAFTE Fatigue Calculator
=============================================================

Modern, publication-quality visualizations based on 2024-2025 best practices
for sleep research, biomathematical modeling, and scientific dashboards.

Key Features:
- Interactive 3D parameter spaces
- Ridge plots for circadian analysis
- Violin + box + swarm overlay plots
- Heatmaps with clustering
- Sankey diagrams for risk factors
- Network visualizations
- Animated time evolution plots
- Publication-quality exports

Dependencies: plotly, matplotlib, seaborn, networkx, scikit-learn
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import networkx as nx
import warnings
warnings.filterwarnings('ignore')

# Set modern plotting styles
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("viridis")

class AdvancedVisualizationSuite:
    """
    Advanced visualization suite for SAFTE fatigue analysis.
    
    Implements cutting-edge scientific visualization techniques optimized
    for sleep research and biomathematical model exploration.
    """
    
    def __init__(self, color_scheme: str = "viridis"):
        """Initialize with perceptually uniform color scheme."""
        self.color_scheme = color_scheme
        self.colors = {
            'optimal': '#2E8B57',      # Sea green
            'moderate': '#FFD700',      # Gold  
            'poor': '#FF8C00',          # Dark orange
            'critical': '#DC143C',      # Crimson
            'sleep': '#4169E1',         # Royal blue
            'circadian': '#8A2BE2'      # Blue violet
        }
    
    def create_3d_parameter_surface(
        self, 
        sleep_durations: List[float],
        sleep_qualities: List[float], 
        performance_matrix: np.ndarray,
        title: str = "Sleep Parameter Optimization Surface"
    ) -> go.Figure:
        """
        Create interactive 3D surface plot for parameter space exploration.
        
        Perfect for visualizing how sleep duration and quality interact
        to affect cognitive performance.
        """
        X, Y = np.meshgrid(sleep_durations, sleep_qualities)
        
        fig = go.Figure(data=[
            go.Surface(
                z=performance_matrix,
                x=X,
                y=Y,
                colorscale=self.color_scheme,
                contours={
                    "z": {"show": True, "usecolormap": True, "highlightcolor": "white", "project_z": True}
                },
                hovertemplate="Duration: %{x:.1f}h<br>Quality: %{y:.2f}<br>Performance: %{z:.1f}%<extra></extra>"
            )
        ])
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            scene=dict(
                xaxis_title="Sleep Duration (hours)",
                yaxis_title="Sleep Quality (0-1)",
                zaxis_title="Cognitive Performance (%)",
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
                aspectmode='cube'
            ),
            width=800,
            height=600,
            template='plotly_white'
        )
        
        return fig
    
    def create_ridge_plot(
        self, 
        df: pd.DataFrame,
        value_col: str = "Performance",
        category_col: str = "Hour",
        title: str = "Circadian Performance Distribution"
    ) -> go.Figure:
        """
        Create ridge plot (joyplot) for circadian analysis.
        
        Shows performance distributions across hours of the day,
        revealing circadian patterns in alertness.
        """
        categories = sorted(df[category_col].unique())
        
        fig = go.Figure()
        
        # Create violin-like ridges
        y_offset = 0
        colors = px.colors.sample_colorscale(self.color_scheme, len(categories))
        
        for i, cat in enumerate(categories):
            data = df[df[category_col] == cat][value_col].values
            
            # Create density curve
            hist, bin_edges = np.histogram(data, bins=50, density=True)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            
            # Normalize density for visual appeal
            hist_normalized = hist / hist.max() * 0.8
            
            # Create filled curve
            fig.add_trace(go.Scatter(
                x=bin_centers,
                y=hist_normalized + y_offset,
                fill='tonexty' if i > 0 else 'tozeroy',
                fillcolor=colors[i],
                line=dict(color=colors[i], width=2),
                name=f"{category_col} {cat}",
                hovertemplate=f"{category_col} {cat}<br>Value: %{{x:.1f}}<br>Density: %{{y:.3f}}<extra></extra>"
            ))
            
            # Add baseline
            fig.add_trace(go.Scatter(
                x=[bin_centers.min(), bin_centers.max()],
                y=[y_offset, y_offset],
                mode='lines',
                line=dict(color='black', width=1),
                showlegend=False
            ))
            
            y_offset += 1
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            xaxis_title=f"{value_col}",
            yaxis=dict(
                tickmode='array',
                tickvals=list(range(len(categories))),
                ticktext=[f"{category_col} {cat}" for cat in categories]
            ),
            showlegend=False,
            template='plotly_white',
            width=800,
            height=600
        )
        
        return fig
    
    def create_violin_swarm_plot(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str = "Performance Distribution Analysis"
    ) -> go.Figure:
        """
        Create violin + box + swarm overlay plot.
        
        Shows distribution, quartiles, and individual data points
        for comprehensive statistical visualization.
        """
        fig = go.Figure()
        
        categories = df[x_col].unique()
        colors = px.colors.sample_colorscale(self.color_scheme, len(categories))
        
        for i, cat in enumerate(categories):
            data = df[df[x_col] == cat][y_col].values
            
            # Add violin plot
            fig.add_trace(go.Violin(
                x=[cat] * len(data),
                y=data,
                name=f"{cat}",
                box_visible=True,
                meanline_visible=True,
                fillcolor=colors[i],
                opacity=0.7,
                line_color='black'
            ))
            
            # Add individual points (swarm-like)
            jitter = np.random.normal(0, 0.04, len(data))
            fig.add_trace(go.Scatter(
                x=[cat] * len(data) + jitter,
                y=data,
                mode='markers',
                marker=dict(
                    size=4,
                    color=colors[i],
                    opacity=0.6,
                    line=dict(width=0.5, color='black')
                ),
                name=f"{cat} points",
                showlegend=False,
                hovertemplate=f"{cat}<br>Value: %{{y:.1f}}<extra></extra>"
            ))
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            xaxis_title=x_col,
            yaxis_title=y_col,
            template='plotly_white',
            width=800,
            height=600
        )
        
        return fig
    
    def create_performance_heatmap(
        self,
        df: pd.DataFrame,
        title: str = "Performance Optimization Heatmap"
    ) -> go.Figure:
        """
        Create clustered heatmap for schedule optimization.
        
        Uses K-means clustering to group similar performance patterns
        and identify optimal sleep/work schedules.
        """
        # Create pivot table for heatmap
        if 'Hour' in df.columns and 'Day' in df.columns:
            pivot = df.pivot_table(
                values='Performance', 
                index='Hour', 
                columns='Day', 
                aggfunc='mean'
            ).fillna(0)
        else:
            # Fallback: create synthetic daily pattern
            hours = np.arange(24)
            days = np.arange(1, 8)
            pivot = pd.DataFrame(
                np.random.rand(24, 7) * 100,
                index=hours,
                columns=days
            )
        
        # Perform clustering on hours
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(pivot.values)
        
        kmeans = KMeans(n_clusters=min(4, len(pivot)), random_state=42)
        clusters = kmeans.fit_predict(scaled_data)
        
        # Create heatmap with cluster annotations
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=[f"Day {d}" for d in pivot.columns],
            y=[f"Hour {h:02d}" for h in pivot.index],
            colorscale=self.color_scheme,
            hovertemplate="Day: %{x}<br>Hour: %{y}<br>Performance: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="Performance (%)")
        ))
        
        # Add cluster annotations
        for i, cluster in enumerate(clusters):
            fig.add_annotation(
                x=-0.15,
                y=i,
                text=f"C{cluster}",
                showarrow=False,
                font=dict(color=px.colors.qualitative.Set1[cluster % 10], size=12),
                xref="paper"
            )
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            template='plotly_white',
            width=800,
            height=600
        )
        
        return fig
    
    def create_fatigue_risk_sankey(
        self,
        risk_factors: Dict[str, float],
        title: str = "Fatigue Risk Factor Flow"
    ) -> go.Figure:
        """
        Create Sankey diagram for fatigue risk factor analysis.
        
        Visualizes how different factors (sleep debt, circadian misalignment,
        workload) contribute to overall fatigue risk.
        """
        # Define nodes
        source_nodes = list(risk_factors.keys())
        intermediate_nodes = ["Sleep Process", "Circadian Process", "Workload Process"]
        target_nodes = ["Fatigue Risk"]
        
        all_nodes = source_nodes + intermediate_nodes + target_nodes
        node_indices = {node: i for i, node in enumerate(all_nodes)}
        
        # Define links (simplified for demonstration)
        links = {
            'source': [],
            'target': [],
            'value': []
        }
        
        # Map risk factors to processes
        process_mapping = {
            'Sleep Debt': 'Sleep Process',
            'Sleep Quality': 'Sleep Process',
            'Circadian Misalignment': 'Circadian Process',
            'Chronotype Offset': 'Circadian Process',
            'Work Hours': 'Workload Process',
            'Cognitive Load': 'Workload Process'
        }
        
        for factor, value in risk_factors.items():
            if factor in process_mapping:
                links['source'].append(node_indices[factor])
                links['target'].append(node_indices[process_mapping[factor]])
                links['value'].append(value)
        
        # Aggregate from processes to final risk
        for process in intermediate_nodes:
            # Sum up inputs to each process
            total_input = sum(
                val for src, tgt, val in zip(links['source'], links['target'], links['value'])
                if all_nodes[tgt] == process
            )
            if total_input > 0:
                links['source'].append(node_indices[process])
                links['target'].append(node_indices['Fatigue Risk'])
                links['value'].append(total_input)
        
        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color="lightblue"
            ),
            link=dict(
                source=links['source'],
                target=links['target'],
                value=links['value'],
                color="rgba(0,0,255,0.3)"
            )
        )])
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            template='plotly_white',
            width=1000,
            height=600
        )
        
        return fig
    
    def create_model_network_diagram(
        self,
        title: str = "SAFTE Model Component Network"
    ) -> go.Figure:
        """
        Create network diagram showing SAFTE model relationships.
        
        Visualizes how different model components (homeostatic, circadian,
        sleep inertia) interact to produce cognitive performance predictions.
        """
        # Create network graph
        G = nx.DiGraph()
        
        # Define nodes with attributes
        nodes = {
            'Sleep Duration': {'type': 'input', 'pos': (0, 1), 'color': self.colors['sleep']},
            'Sleep Quality': {'type': 'input', 'pos': (0, 0), 'color': self.colors['sleep']},
            'Circadian Phase': {'type': 'input', 'pos': (0, -1), 'color': self.colors['circadian']},
            'Homeostatic Process': {'type': 'process', 'pos': (2, 0.5), 'color': '#1f77b4'},
            'Circadian Process': {'type': 'process', 'pos': (2, -0.5), 'color': self.colors['circadian']},
            'Sleep Inertia': {'type': 'process', 'pos': (2, 1.5), 'color': '#ff7f0e'},
            'Cognitive Performance': {'type': 'output', 'pos': (4, 0), 'color': self.colors['optimal']},
            'Task Effectiveness': {'type': 'output', 'pos': (4, 1), 'color': self.colors['moderate']}
        }
        
        # Add nodes to graph
        for node, attrs in nodes.items():
            G.add_node(node, **attrs)
        
        # Define edges with weights
        edges = [
            ('Sleep Duration', 'Homeostatic Process', 0.8),
            ('Sleep Quality', 'Homeostatic Process', 0.6),
            ('Sleep Duration', 'Sleep Inertia', 0.4),
            ('Circadian Phase', 'Circadian Process', 1.0),
            ('Homeostatic Process', 'Cognitive Performance', 0.7),
            ('Circadian Process', 'Cognitive Performance', 0.5),
            ('Sleep Inertia', 'Cognitive Performance', 0.3),
            ('Cognitive Performance', 'Task Effectiveness', 0.9)
        ]
        
        G.add_weighted_edges_from(edges)
        
        # Extract positions and create traces
        pos = nx.get_node_attributes(G, 'pos')
        
        # Create edge traces
        edge_x, edge_y = [], []
        edge_weights = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_weights.append(G[edge[0]][edge[1]]['weight'])
        
        # Create node traces
        node_x = [pos[node][0] for node in G.nodes()]
        node_y = [pos[node][1] for node in G.nodes()]
        node_colors = [nodes[node]['color'] for node in G.nodes()]
        node_text = list(G.nodes())
        
        # Create figure
        fig = go.Figure()
        
        # Add edges
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            mode='lines',
            name='Connections'
        ))
        
        # Add nodes
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            textfont=dict(size=10, color='white'),
            marker=dict(
                size=40,
                color=node_colors,
                line=dict(width=2, color='black')
            ),
            name='Model Components'
        ))
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template='plotly_white',
            width=800,
            height=600,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        return fig
    
    def create_animated_evolution_plot(
        self,
        df: pd.DataFrame,
        title: str = "Performance Evolution Animation"
    ) -> go.Figure:
        """
        Create animated plot showing performance evolution over time.
        
        Animates how performance changes throughout days, with slider controls
        for interactive temporal exploration.
        """
        if 'Day' not in df.columns:
            df['Day'] = (df.index // 24) + 1
        
        fig = go.Figure()
        
        days = sorted(df['Day'].unique())
        
        # Create frames for animation
        frames = []
        for day in days:
            day_data = df[df['Day'] <= day]
            
            frame = go.Frame(
                data=[
                    go.Scatter(
                        x=day_data.index,
                        y=day_data['Performance'],
                        mode='lines',
                        line=dict(color=self.colors['optimal'], width=3),
                        name='Performance'
                    ),
                    go.Scatter(
                        x=day_data.index[-1:] if not day_data.empty else [],
                        y=day_data['Performance'].iloc[-1:] if not day_data.empty else [],
                        mode='markers',
                        marker=dict(size=12, color='red'),
                        name='Current'
                    )
                ],
                name=str(day)
            )
            frames.append(frame)
        
        # Add initial traces
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines',
            line=dict(color=self.colors['optimal'], width=3),
            name='Performance'
        ))
        
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='markers',
            marker=dict(size=12, color='red'),
            name='Current'
        ))
        
        fig.frames = frames
        
        # Add play/pause buttons
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 16, 'family': 'Arial, sans-serif'}
            },
            xaxis_title="Time (hours)",
            yaxis_title="Performance (%)",
            updatemenus=[{
                'type': 'buttons',
                'showactive': False,
                'x': 0.1,
                'y': 0,
                'buttons': [
                    {
                        'label': 'Play',
                        'method': 'animate',
                        'args': [None, {
                            'frame': {'duration': 500, 'redraw': True},
                            'transition': {'duration': 300}
                        }]
                    },
                    {
                        'label': 'Pause',
                        'method': 'animate',
                        'args': [[None], {
                            'frame': {'duration': 0, 'redraw': False},
                            'mode': 'immediate',
                            'transition': {'duration': 0}
                        }]
                    }
                ]
            }],
            sliders=[{
                'steps': [
                    {
                        'args': [[str(day)], {
                            'frame': {'duration': 300, 'redraw': True},
                            'mode': 'immediate',
                            'transition': {'duration': 300}
                        }],
                        'label': f'Day {day}',
                        'method': 'animate'
                    } for day in days
                ],
                'active': 0,
                'currentvalue': {'prefix': 'Day: '},
                'transition': {'duration': 300},
                'x': 0.1,
                'len': 0.9
            }],
            template='plotly_white',
            width=900,
            height=600
        )
        
        return fig
    
    def create_multi_panel_dashboard(
        self,
        df: pd.DataFrame,
        title: str = "Comprehensive Performance Dashboard"
    ) -> go.Figure:
        """
        Create comprehensive multi-panel dashboard.
        
        Combines multiple visualization types in a single,
        publication-quality dashboard layout.
        """
        # Create subplots
        fig = make_subplots(
            rows=3, cols=3,
            subplot_titles=(
                "Performance Over Time", "Performance Distribution", "Daily Averages",
                "Circadian Pattern", "Risk Assessment", "Sleep Quality Impact",
                "Fatigue Accumulation", "Recovery Patterns", "Performance Zones"
            ),
            specs=[
                [{"type": "scatter"}, {"type": "histogram"}, {"type": "bar"}],
                [{"type": "polar"}, {"type": "indicator"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "heatmap"}, {"type": "pie"}]
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.08
        )
        
        # 1. Performance over time
        fig.add_trace(
            go.Scatter(
                x=df.index, 
                y=df['Performance'],
                mode='lines',
                name='Performance',
                line=dict(color=self.colors['optimal'], width=2)
            ),
            row=1, col=1
        )
        
        # 2. Performance distribution
        fig.add_trace(
            go.Histogram(
                x=df['Performance'],
                nbinsx=20,
                name='Distribution',
                marker_color=self.colors['moderate']
            ),
            row=1, col=2
        )
        
        # 3. Daily averages (if Day column exists)
        if 'Day' in df.columns:
            daily_avg = df.groupby('Day')['Performance'].mean()
            fig.add_trace(
                go.Bar(
                    x=daily_avg.index,
                    y=daily_avg.values,
                    name='Daily Avg',
                    marker_color=self.colors['sleep']
                ),
                row=1, col=3
            )
        
        # 4. Circadian pattern (polar plot)
        if 'Hour' in df.columns:
            hourly_avg = df.groupby('Hour')['Performance'].mean()
            fig.add_trace(
                go.Scatterpolar(
                    r=hourly_avg.values,
                    theta=[f"{h}:00" for h in hourly_avg.index],
                    mode='lines+markers',
                    name='Circadian',
                    line=dict(color=self.colors['circadian'])
                ),
                row=2, col=1
            )
        
        # 5. Risk indicator
        risk_level = (df['Performance'] < 70).mean() * 100
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=risk_level,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Risk %"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkred"},
                    'steps': [
                        {'range': [0, 25], 'color': "lightgray"},
                        {'range': [25, 50], 'color': "yellow"},
                        {'range': [50, 75], 'color': "orange"},
                        {'range': [75, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ),
            row=2, col=2
        )
        
        # 6. Sleep quality impact (scatter)
        if 'Sleep_Quality' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['Sleep_Quality'],
                    y=df['Performance'],
                    mode='markers',
                    name='Quality Impact',
                    marker=dict(color=self.colors['sleep'], opacity=0.6)
                ),
                row=2, col=3
            )
        
        # Update layout
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {'size': 18, 'family': 'Arial, sans-serif'}
            },
            template='plotly_white',
            width=1200,
            height=900,
            showlegend=False
        )
        
        return fig

def create_publication_export(
    fig: go.Figure,
    filename: str,
    width: int = 800,
    height: int = 600,
    dpi: int = 300
) -> str:
    """
    Export figure in publication-quality formats.
    
    Supports PNG, PDF, SVG, and HTML formats with high DPI
    and proper font rendering for scientific publications.
    """
    
    # Configure for publication quality
    fig.update_layout(
        font=dict(family="Arial, sans-serif", size=12),
        width=width,
        height=height,
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    # Export in multiple formats
    formats = {
        'png': f'{filename}.png',
        'pdf': f'{filename}.pdf', 
        'svg': f'{filename}.svg',
        'html': f'{filename}.html'
    }
    
    for fmt, filepath in formats.items():
        try:
            if fmt == 'html':
                fig.write_html(filepath)
            else:
                fig.write_image(filepath, format=fmt, width=width, height=height, scale=dpi/100)
        except Exception as e:
            print(f"Warning: Could not export {fmt} format: {e}")
    
    return f"Exported to: {', '.join(formats.values())}"

# Example usage and demo functions
def demo_advanced_visualizations():
    """Demonstrate advanced visualization capabilities."""
    
    # Create sample data
    np.random.seed(42)
    n_points = 1000
    
    df = pd.DataFrame({
        'Performance': np.random.beta(2, 1) * 100,
        'Hour': np.random.randint(0, 24, n_points),
        'Day': np.random.randint(1, 8, n_points),
        'Sleep_Duration': np.random.uniform(4, 10, n_points),
        'Sleep_Quality': np.random.uniform(0.5, 1.0, n_points)
    })
    
    # Initialize visualization suite
    viz = AdvancedVisualizationSuite()
    
    print("Creating advanced visualizations...")
    
    # Create 3D surface
    sleep_durations = np.linspace(4, 10, 20)
    sleep_qualities = np.linspace(0.5, 1.0, 20)
    X, Y = np.meshgrid(sleep_durations, sleep_qualities)
    Z = 60 + 30 * X/10 + 20 * Y + np.random.normal(0, 5, X.shape)
    
    fig_3d = viz.create_3d_parameter_surface(
        sleep_durations.tolist(),
        sleep_qualities.tolist(),
        Z
    )
    
    # Create ridge plot
    fig_ridge = viz.create_ridge_plot(df)
    
    # Create violin plot
    df['Sleep_Category'] = pd.cut(df['Sleep_Duration'], 
                                 bins=[0, 6, 7, 8, 12], 
                                 labels=['Short', 'Normal', 'Long', 'Extended'])
    fig_violin = viz.create_violin_swarm_plot(df, 'Sleep_Category', 'Performance')
    
    # Create risk factors Sankey
    risk_factors = {
        'Sleep Debt': 15,
        'Sleep Quality': 10, 
        'Circadian Misalignment': 8,
        'Work Hours': 12,
        'Cognitive Load': 6
    }
    fig_sankey = viz.create_fatigue_risk_sankey(risk_factors)
    
    # Create network diagram
    fig_network = viz.create_model_network_diagram()
    
    return {
        '3d_surface': fig_3d,
        'ridge_plot': fig_ridge,
        'violin_plot': fig_violin,
        'sankey': fig_sankey,
        'network': fig_network
    }

if __name__ == "__main__":
    figures = demo_advanced_visualizations()
    print("Advanced visualizations created successfully!")
    
    # Export examples
    for name, fig in figures.items():
        create_publication_export(fig, f"demo_{name}")
